import assert from 'node:assert/strict';
import { test } from 'node:test';
import { IncomingMessage, ServerResponse } from 'node:http';
import { Socket } from 'node:net';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from './app.js';

async function fixture(path = ':memory:') {
  const instance = createApp(path);
  // Exercise the complete Express middleware stack without binding a network port.
  function inject(path: string, method: string, body?: string): Promise<Response> {
    return new Promise((resolve, reject) => {
      const req = new IncomingMessage(new Socket());
      req.url = path;
      req.method = method;
      req.headers = { 'content-type': 'application/json' };
      if (body !== undefined) req.headers['content-length'] = String(Buffer.byteLength(body));
      const res = new ServerResponse(req);
      const chunks: Buffer[] = [];
      res.write = ((chunk: string | Uint8Array) => {
        chunks.push(Buffer.from(chunk));
        return true;
      }) as typeof res.write;
      res.end = ((chunk?: string | Uint8Array) => {
        if (chunk) chunks.push(Buffer.from(chunk));
        const headers = new Headers();
        for (const [key, value] of Object.entries(res.getHeaders())) {
          if (value !== undefined) headers.set(key, String(value));
        }
        resolve(new Response(Buffer.concat(chunks), { status: res.statusCode, headers }));
        return res;
      }) as typeof res.end;
      req.on('error', reject);
      instance.app(req, res);
      if (body !== undefined) req.push(Buffer.from(body));
      req.push(null);
    });
  }
  return {
    request: (path: string, method = 'GET', body?: unknown) =>
      inject(path, method, body === undefined ? undefined : JSON.stringify(body)),
    raw: (body: string) => inject('/books', 'POST', body),
    close: async () => instance.close(),
  };
}
const sample = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' };

test('CRUD lifecycle returns JSON and appropriate statuses', async t => {
  const f = await fixture(); t.after(f.close);
  assert.deepEqual(await (await f.request('/books')).json(), []);
  const created = await f.request('/books', 'POST', sample);
  assert.equal(created.status, 201);
  const book = await created.json();
  assert.equal(created.headers.get('location'), `/books/${book.id}`);
  assert.deepEqual(book, { id: book.id, ...sample });
  assert.deepEqual(await (await f.request(`/books/${book.id}`)).json(), book);
  const update = await f.request(`/books/${book.id}`, 'PUT', { title: 'Updated', author: 'Someone' });
  assert.equal(update.status, 200);
  assert.deepEqual(await update.json(), { id: book.id, title: 'Updated', author: 'Someone', year: null, isbn: null });
  assert.equal((await f.request(`/books/${book.id}`, 'DELETE')).status, 200);
  assert.equal((await f.request(`/books/${book.id}`)).status, 404);
  assert.deepEqual(await (await f.request('/books')).json(), []);
});

test('author filter is exact and handles SQL-like input safely', async t => {
  const f = await fixture(); t.after(f.close);
  await f.request('/books', 'POST', sample);
  await f.request('/books', 'POST', { title: 'Other', author: 'Different' });
  const books = await (await f.request('/books?author=Frank%20Herbert')).json();
  assert.equal(books.length, 1);
  assert.equal(books[0].title, 'Dune');
  assert.deepEqual(await (await f.request('/books?author=%27%20OR%201%3D1--')).json(), []);
  assert.equal((await f.request('/books?author=a&author=b')).status, 400);
});

test('validates required fields, optional types, and malformed JSON', async t => {
  const f = await fixture(); t.after(f.close);
  for (const body of [{}, { title: ' ' , author: 'A' }, { title: 'T' },
    { ...sample, author: 7 }, { ...sample, year: '1965' }, { ...sample, year: 1.5 },
    { ...sample, isbn: 123 }, [], null]) {
    const response = await f.request('/books', 'POST', body);
    assert.equal(response.status, 400);
    assert.equal(typeof (await response.json()).error, 'string');
  }
  assert.equal((await f.raw('{bad')).status, 400);
  assert.equal((await f.raw(JSON.stringify({ ...sample, title: 'x'.repeat(110000) }))).status, 413);
  const created = await (await f.request('/books', 'POST', sample)).json();
  assert.equal((await f.request(`/books/${created.id}`, 'PUT', { title: '' })).status, 400);
  assert.deepEqual(await (await f.request(`/books/${created.id}`)).json(), created);
});

test('health, invalid IDs, missing books, and unknown routes', async t => {
  const f = await fixture(); t.after(f.close);
  const health = await f.request('/health');
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { status: 'ok' });
  for (const method of ['GET', 'PUT', 'DELETE']) {
    assert.equal((await f.request('/books/999', method, method === 'PUT' ? sample : undefined)).status, 404);
    assert.equal((await f.request('/books/abc', method)).status, 400);
  }
  const missing = await f.request('/unknown');
  assert.equal(missing.status, 404);
  assert.deepEqual(await missing.json(), { error: 'Route not found' });
});

test('SQLite data persists when the service is reopened', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'books-test-'));
  try {
    const path = join(dir, 'books.sqlite');
    const first = await fixture(path);
    let book;
    try { book = await (await first.request('/books', 'POST', sample)).json(); }
    finally { await first.close(); }
    const second = await fixture(path);
    try { assert.deepEqual(await (await second.request(`/books/${book.id}`)).json(), book); }
    finally { await second.close(); }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
