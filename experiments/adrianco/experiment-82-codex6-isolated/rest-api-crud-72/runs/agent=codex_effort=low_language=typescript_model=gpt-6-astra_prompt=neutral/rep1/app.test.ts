import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from './app.js';

async function start(path = ':memory:') {
  const server = createApp(path);
  return {
    request: (path: string, method = 'GET', body?: unknown, contentType = 'application/json', raw = false): Promise<Response> => {
      const req = Object.assign(Readable.from(body === undefined ? [] : [Buffer.from(raw ? String(body) : JSON.stringify(body))]), {
        url: path, method, headers: { 'content-type': contentType },
      });
      return new Promise(resolve => {
        const headers = new Headers();
        let status = 200;
        const res = {
          setHeader(name: string, value: string) { headers.set(name, value); },
          writeHead(code: number, values: Record<string, string>) {
            status = code;
            for (const [name, value] of Object.entries(values)) headers.set(name, value);
          },
          end(data: string) { resolve(new Response(data, { status, headers })); },
        };
        server.emit('request', req, res);
      });
    },
    close: async () => { server.emit('close'); },
  };
}
const book = { title: 'A Wizard of Earthsea', author: 'Ursula K. Le Guin', year: 1968, isbn: '9780547773742' };

test('health and complete book lifecycle', async () => {
  const app = await start();
  try {
    const health = await app.request('/health');
    assert.equal(health.status, 200);
    assert.deepEqual(await health.json(), { status: 'ok' });
    assert.deepEqual(await (await app.request('/books')).json(), []);
    const created = await app.request('/books', 'POST', book);
    assert.equal(created.status, 201);
    assert.equal(created.headers.get('location'), '/books/1');
    assert.deepEqual(await created.json(), { id: 1, ...book });
    assert.deepEqual(await (await app.request('/books/1')).json(), { id: 1, ...book });
    const updated = await app.request('/books/1', 'PUT', { title: 'The Tombs of Atuan', author: book.author });
    assert.equal(updated.status, 200);
    assert.deepEqual(await updated.json(), { id: 1, title: 'The Tombs of Atuan', author: book.author, year: null, isbn: null });
    assert.equal((await app.request('/books/1', 'DELETE')).status, 200);
    assert.equal((await app.request('/books/1')).status, 404);
    assert.deepEqual(await (await app.request('/books')).json(), []);
  } finally { await app.close(); }
});

test('author filter matches exactly and treats SQL as data', async () => {
  const app = await start();
  try {
    await app.request('/books', 'POST', book);
    await app.request('/books', 'POST', { ...book, author: 'Someone Else' });
    assert.equal((await (await app.request('/books')).json() as unknown[]).length, 2);
    assert.deepEqual(await (await app.request(`/books?author=${encodeURIComponent(book.author)}`)).json(), [{ id: 1, ...book }]);
    assert.deepEqual(await (await app.request('/books?author=%27%20OR%201%3D1--')).json(), []);
  } finally { await app.close(); }
});

test('invalid input is rejected without mutating records', async () => {
  const app = await start();
  try {
    for (const body of [{}, { title: 'Book' }, { author: 'Author' }, { ...book, title: '  ' }, { ...book, author: 42 }, { ...book, year: 1.5 }, { ...book, isbn: 123 }, [], null]) {
      const response = await app.request('/books', 'POST', body);
      assert.equal(response.status, 400);
      assert.equal(typeof (await response.json() as { error: string }).error, 'string');
    }
    assert.deepEqual(await (await app.request('/books')).json(), []);
    await app.request('/books', 'POST', book);
    assert.equal((await app.request('/books/1', 'PUT', { title: 'Invalid' })).status, 400);
    assert.deepEqual(await (await app.request('/books/1')).json(), { id: 1, ...book });
  } finally { await app.close(); }
});

test('missing books, invalid IDs, unknown routes and methods have JSON errors', async () => {
  const app = await start();
  try {
    for (const method of ['GET', 'PUT', 'DELETE']) {
      assert.equal((await app.request('/books/999', method, method === 'PUT' ? book : undefined)).status, 404);
    }
    for (const id of ['abc', '0', '-1', '1.5', '9007199254740992']) {
      assert.equal((await app.request(`/books/${id}`)).status, 400);
    }
    const unknown = await app.request('/unknown');
    assert.equal(unknown.status, 404);
    assert.match(unknown.headers.get('content-type')!, /application\/json/);
    assert.equal((await app.request('/books', 'PATCH')).status, 405);
  } finally { await app.close(); }
});

test('file database persists across application restarts', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'book-api-'));
  try {
    const path = join(directory, 'books.sqlite');
    const first = await start(path);
    try { assert.equal((await first.request('/books', 'POST', book)).status, 201); }
    finally { await first.close(); }
    const second = await start(path);
    try { assert.deepEqual(await (await second.request('/books/1')).json(), { id: 1, ...book }); }
    finally { await second.close(); }
  } finally { await rm(directory, { recursive: true, force: true }); }
});


test('malformed JSON, media types and oversized bodies are rejected', async () => {
  const app = await start();
  try {
    assert.equal((await app.request('/books', 'POST', '{', 'application/json', true)).status, 400);
    assert.equal((await app.request('/books', 'POST', book, 'text/plain')).status, 415);
    assert.equal((await app.request('/books', 'POST', { ...book, title: 'x'.repeat(65536) })).status, 413);
    assert.deepEqual(await (await app.request('/books')).json(), []);
  } finally { await app.close(); }
});
