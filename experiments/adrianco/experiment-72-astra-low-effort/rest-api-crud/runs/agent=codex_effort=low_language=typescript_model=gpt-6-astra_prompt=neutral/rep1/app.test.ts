import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createServer, request as httpRequest } from 'node:http';
import { Duplex, PassThrough } from 'node:stream';
import type { Socket } from 'node:net';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from './app.js';
import { BookStore } from './store.js';

function fixture(t: import('node:test').TestContext) {
  const store = new BookStore();
  const server = createServer(createApp(store));
  t.after(() => store.close());
  return async (path: string, method = 'GET', body?: unknown, raw = false) => {
    const payload = body === undefined ? undefined : raw ? String(body) : JSON.stringify(body);
    const clientToServer = new PassThrough();
    const serverToClient = new PassThrough();
    const client = Duplex.from({ readable: serverToClient, writable: clientToServer });
    const socket = Duplex.from({ readable: clientToServer, writable: serverToClient });
    client.on('error', () => {});
    socket.on('error', () => {});
    server.emit('connection', socket);
    try {
      return await new Promise<{ status: number; body: any; headers: Headers }>((resolve, reject) => {
        const req = httpRequest({
          path, method,
          createConnection: () => client as Socket,
          headers: payload === undefined ? {} : {
            'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload),
          },
        }, res => {
          const chunks: Buffer[] = [];
          res.on('data', chunk => chunks.push(Buffer.from(chunk)));
          res.on('error', reject);
          res.on('end', () => {
            try {
              assert.match(res.headers['content-type']!, /application\/json/);
              const headers = new Headers();
              for (const [key, value] of Object.entries(res.headers)) {
                if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
              }
              resolve({ status: res.statusCode!, body: JSON.parse(Buffer.concat(chunks).toString()), headers });
            } catch (error) { reject(error); }
          });
        });
        req.on('error', reject);
        req.end(payload);
      });
    } finally {
      client.destroy();
      socket.destroy();
    }
  };
}
const book = { title: 'The Left Hand of Darkness', author: 'Ursula K. Le Guin', year: 1969, isbn: '9780441478125' };

test('create, read, replace, and delete a book through HTTP', async t => {
  const request = await fixture(t);
  assert.deepEqual((await request('/books')).body, []);
  const created = await request('/books', 'POST', book);
  assert.equal(created.status, 201);
  assert.deepEqual(created.body, { id: 1, ...book });
  assert.equal(created.headers.get('location'), '/books/1');
  assert.deepEqual((await request('/books/1')).body, created.body);
  const updated = await request('/books/1', 'PUT', { title: '  A Wizard of Earthsea ', author: book.author });
  assert.equal(updated.status, 200);
  assert.deepEqual(updated.body, { id: 1, title: 'A Wizard of Earthsea', author: book.author, year: null, isbn: null });
  assert.deepEqual((await request('/books/1')).body, updated.body);
  assert.equal((await request('/books/1', 'DELETE')).status, 200);
  assert.equal((await request('/books/1')).status, 404);
  assert.deepEqual((await request('/books')).body, []);
});

test('list filters by exact author and treats SQL-like input as data', async t => {
  const request = await fixture(t);
  await request('/books', 'POST', book);
  await request('/books', 'POST', { title: 'Dune', author: 'Frank Herbert' });
  assert.equal((await request('/books')).body.length, 2);
  const filtered = await request('/books?author=' + encodeURIComponent(book.author));
  assert.equal(filtered.body.length, 1);
  assert.equal(filtered.body[0].title, book.title);
  assert.deepEqual((await request('/books?author=unknown')).body, []);
  assert.deepEqual((await request('/books?author=' + encodeURIComponent("' OR 1=1 --"))).body, []);
  assert.equal((await request('/books?author=a&author=b')).status, 400);
});

test('invalid payloads are rejected without creating or changing books', async t => {
  const request = await fixture(t);
  const invalid = [null, [], {}, { title: 'A' }, { author: 'B' }, { title: ' ', author: 'B' },
    { ...book, author: 12 }, { ...book, year: '1969' }, { ...book, year: 1.5 },
    { ...book, isbn: 123 }, { ...book, isbn: '' }];
  for (const body of invalid) assert.equal((await request('/books', 'POST', body)).status, 400);
  assert.deepEqual((await request('/books')).body, []);
  await request('/books', 'POST', book);
  for (const body of invalid) assert.equal((await request('/books/1', 'PUT', body)).status, 400);
  assert.deepEqual((await request('/books/1')).body, { id: 1, ...book });
});

test('missing books, invalid IDs, health, and unknown routes return JSON statuses', async t => {
  const request = await fixture(t);
  assert.deepEqual((await request('/health')).body, { status: 'ok' });
  assert.equal((await request('/health')).status, 200);
  for (const method of ['GET', 'PUT', 'DELETE']) {
    assert.equal((await request('/books/999', method, method === 'PUT' ? book : undefined)).status, 404);
    for (const id of ['abc', '0', '-1', '1.5', '9007199254740992']) {
      assert.equal((await request(`/books/${id}`, method, method === 'PUT' ? book : undefined)).status, 400);
    }
  }
  assert.equal((await request('/unknown')).status, 404);
});

test('malformed JSON and oversized requests produce JSON errors', async t => {
  const request = fixture(t);
  for (const [body, expected] of [['{bad', 400], [JSON.stringify({ ...book, title: 'x'.repeat(110_000) }), 413]] as const) {
    const response = await request('/books', 'POST', body, true);
    assert.equal(response.status, expected);
    assert.equal(typeof response.body.error, 'string');
  }
  assert.deepEqual((await request('/books')).body, []);
});

test('SQLite persists created, updated, and deleted records across reopening', () => {
  const directory = mkdtempSync(join(tmpdir(), 'books-test-'));
  const path = join(directory, 'books.sqlite');
  let store = new BookStore(path);
  try {
    const created = store.create(book);
    store.close();
    store = new BookStore(path);
    assert.deepEqual(store.get(created.id), created);
    store.update(created.id, { ...book, title: 'Updated' });
    store.close();
    store = new BookStore(path);
    assert.equal(store.get(created.id)?.title, 'Updated');
    store.delete(created.id);
    store.close();
    store = new BookStore(path);
    assert.deepEqual(store.list(), []);
  } finally {
    store.close();
    rmSync(directory, { recursive: true, force: true });
  }
});
