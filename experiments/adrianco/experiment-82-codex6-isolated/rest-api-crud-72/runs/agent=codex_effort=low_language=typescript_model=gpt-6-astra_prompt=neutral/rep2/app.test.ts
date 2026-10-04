import assert from 'node:assert/strict';
import { test } from 'node:test';
import { IncomingMessage, ServerResponse } from 'node:http';
import { Socket } from 'node:net';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from './app.js';

async function fixture(path = ':memory:') {
  const { app, close } = createApp(path);
  // Exercise the actual Express middleware using Node HTTP objects without a port.
  const request = (path: string, method = 'GET', body?: unknown, raw?: string) =>
    new Promise<{ status: number; headers: Headers; json: () => Promise<any> }>((resolve, reject) => {
      const socket = new Socket();
      const req = new IncomingMessage(socket);
      req.method = method;
      req.url = path;
      const payload = raw ?? (body === undefined ? undefined : JSON.stringify(body));
      req.headers = { 'content-type': 'application/json' };
      if (payload !== undefined) req.headers['content-length'] = String(Buffer.byteLength(payload));
      const res = new ServerResponse(req);
      const chunks: Buffer[] = [];
      // Capture the response body at Node's response boundary, before socket I/O.
      res.write = ((chunk: string | Buffer) => {
        chunks.push(Buffer.from(chunk));
        return true;
      }) as typeof res.write;
      res.end = ((chunk?: string | Buffer) => {
        if (chunk) chunks.push(Buffer.from(chunk));
        const headers = new Headers();
        for (const [name, value] of Object.entries(res.getHeaders())) {
          if (value !== undefined) headers.set(name, String(value));
        }
        resolve({ status: res.statusCode, headers, json: async () => JSON.parse(Buffer.concat(chunks).toString()) });
        socket.destroy();
        return res;
      }) as typeof res.end;
      req.on('error', reject);
      app(req, res);
      if (payload !== undefined) req.push(Buffer.from(payload));
      req.push(null);
    });
  return { request, stop: async () => close() };
}
const input = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' };

test('health and initially empty collection return JSON', async t => {
  const f = await fixture(); t.after(f.stop);
  const health = await f.request('/health');
  assert.equal(health.status, 200);
  assert.match(health.headers.get('content-type')!, /application\/json/);
  assert.deepEqual(await health.json(), { status: 'ok' });
  assert.deepEqual(await (await f.request('/books')).json(), []);
});

test('create, retrieve, replace and delete a book', async t => {
  const f = await fixture(); t.after(f.stop);
  const response = await f.request('/books', 'POST', input);
  assert.equal(response.status, 201);
  const book = await response.json();
  assert.deepEqual(book, { id: 1, ...input });
  assert.equal(response.headers.get('location'), '/books/1');
  assert.deepEqual(await (await f.request('/books/1')).json(), book);
  const update = await f.request('/books/1', 'PUT', { title: ' Dune Messiah ', author: input.author });
  assert.equal(update.status, 200);
  const expected = { id: 1, title: 'Dune Messiah', author: input.author, year: null, isbn: null };
  assert.deepEqual(await update.json(), expected);
  assert.deepEqual(await (await f.request('/books/1')).json(), expected);
  assert.equal((await f.request('/books/1', 'DELETE')).status, 200);
  assert.equal((await f.request('/books/1')).status, 404);
  assert.deepEqual(await (await f.request('/books')).json(), []);
});

test('author filter matches exactly and treats SQL as data', async t => {
  const f = await fixture(); t.after(f.stop);
  await f.request('/books', 'POST', input);
  await f.request('/books', 'POST', { title: 'Other', author: 'Someone Else' });
  const books = await (await f.request('/books?author=Frank%20Herbert')).json();
  assert.equal(books.length, 1);
  assert.equal(books[0].title, 'Dune');
  assert.equal((await (await f.request('/books')).json()).length, 2);
  assert.deepEqual(await (await f.request('/books?author=' + encodeURIComponent("' OR 1=1 --"))).json(), []);
  assert.equal((await f.request('/books?author=a&author=b')).status, 400);
});

test('invalid bodies are rejected without changing stored data', async t => {
  const f = await fixture(); t.after(f.stop);
  for (const body of [{}, { title: 'x' }, { author: 'x' }, { title: ' ', author: 'x' },
    { title: 'x', author: 42 }, { ...input, year: '1965' }, { ...input, year: 1.5 },
    { ...input, isbn: 123 }, { ...input, isbn: '' }, [], null]) {
    assert.equal((await f.request('/books', 'POST', body)).status, 400);
  }
  const malformed = await f.request('/books', 'POST', undefined, '{');
  assert.equal(malformed.status, 400);
  assert.equal(typeof (await malformed.json()).error, 'string');
  assert.deepEqual(await (await f.request('/books')).json(), []);
  await f.request('/books', 'POST', input);
  assert.equal((await f.request('/books/1', 'PUT', { title: '' })).status, 400);
  assert.deepEqual(await (await f.request('/books/1')).json(), { id: 1, ...input });
});

test('missing books, invalid IDs and unknown routes have JSON errors', async t => {
  const f = await fixture(); t.after(f.stop);
  for (const method of ['GET', 'PUT', 'DELETE']) {
    assert.equal((await f.request('/books/999', method, method === 'PUT' ? input : undefined)).status, 404);
    for (const id of ['abc', '0', '-1', '1.2', '9007199254740992']) {
      assert.equal((await f.request(`/books/${id}`, method, method === 'PUT' ? input : undefined)).status, 400);
    }
  }
  const missing = await f.request('/unknown');
  assert.equal(missing.status, 404);
  assert.equal(typeof (await missing.json()).error, 'string');
});

test('books persist when the database is reopened', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'books-test-'));
  try {
    const path = join(directory, 'books.sqlite');
    const first = await fixture(path);
    try { assert.equal((await first.request('/books', 'POST', input)).status, 201); }
    finally { await first.stop(); }
    const second = await fixture(path);
    try { assert.deepEqual(await (await second.request('/books/1')).json(), { id: 1, ...input }); }
    finally { await second.stop(); }
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
