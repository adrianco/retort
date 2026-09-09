import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from './api.js';

async function start(path = ':memory:') {
  const server = createApp(path);
  function rawRequest(path: string, method = 'GET', body?: string, contentType = 'application/json'): Promise<Response> {
    return new Promise(resolve => {
      const req = Object.assign(Readable.from(body === undefined ? [] : [Buffer.from(body)]), {
        url: path, method, headers: body === undefined ? {} : { 'content-type': contentType },
      });
      const headers = new Headers();
      let status = 200;
      const res = {
        destroyed: false,
        setHeader(name: string, value: string) { headers.set(name, value); },
        writeHead(code: number, values: Record<string, string> = {}) {
          status = code;
          for (const [name, value] of Object.entries(values)) headers.set(name, value);
        },
        end(value?: string) { resolve(new Response(value ?? null, { status, headers })); },
      };
      server.emit('request', req, res);
    });
  }
  return {
    rawRequest,
    request: (path: string, method = 'GET', body?: unknown) => rawRequest(path, method, body === undefined ? undefined : JSON.stringify(body)),
    close: async () => { server.emit('close'); },
  };
}
const book = { title: 'A Wizard of Earthsea', author: 'Ursula K. Le Guin', year: 1968, isbn: '9780547773742' };

test('health and complete book lifecycle', async t => {
  const app = await start(); t.after(app.close);
  assert.deepEqual(await (await app.request('/health')).json(), { status: 'ok' });
  assert.deepEqual(await (await app.request('/books')).json(), []);
  const created = await app.request('/books', 'POST', book);
  assert.equal(created.status, 201);
  const record = await created.json() as typeof book & { id: number };
  assert.deepEqual(record, { id: 1, ...book });
  assert.equal(created.headers.get('location'), '/books/1');
  assert.deepEqual(await (await app.request('/books/1')).json(), record);
  const updated = await app.request('/books/1', 'PUT', { title: 'Tehanu', author: book.author });
  assert.equal(updated.status, 200);
  assert.deepEqual(await updated.json(), { id: 1, title: 'Tehanu', author: book.author, year: null, isbn: null });
  const deleted = await app.request('/books/1', 'DELETE');
  assert.equal(deleted.status, 204); assert.equal(await deleted.text(), '');
  assert.equal((await app.request('/books/1')).status, 404);
  assert.deepEqual(await (await app.request('/books')).json(), []);
});

test('author filter uses exact matching and safely handles SQL-like text', async t => {
  const app = await start(); t.after(app.close);
  await app.request('/books', 'POST', book);
  await app.request('/books', 'POST', { title: 'Other', author: 'Other Author' });
  const filtered = await (await app.request(`/books?author=${encodeURIComponent(book.author)}`)).json() as unknown[];
  assert.equal(filtered.length, 1);
  assert.deepEqual(await (await app.request(`/books?author=${encodeURIComponent("' OR 1=1 --")}`)).json(), []);
  assert.equal((await (await app.request('/books')).json() as unknown[]).length, 2);
});

test('invalid input is rejected without modifying data', async t => {
  const app = await start(); t.after(app.close);
  for (const invalid of [{}, { title: ' ' , author: 'X' }, { title: 'X' }, { ...book, author: 1 }, { ...book, year: 1.5 }, { ...book, isbn: 123 }, [], null]) {
    const response = await app.request('/books', 'POST', invalid);
    assert.equal(response.status, 400);
    assert.equal(typeof (await response.json() as { error: string }).error, 'string');
  }
  await app.request('/books', 'POST', book);
  assert.equal((await app.request('/books/1', 'PUT', { title: 'Missing author' })).status, 400);
  assert.deepEqual(await (await app.request('/books/1')).json(), { id: 1, ...book });
});

test('missing records, bad IDs, routes and unsupported methods', async t => {
  const app = await start(); t.after(app.close);
  for (const method of ['GET', 'PUT', 'DELETE']) assert.equal((await app.request('/books/999', method, method === 'PUT' ? book : undefined)).status, 404);
  for (const id of ['0', '-1', 'abc', '1.5', '9007199254740992']) assert.equal((await app.request(`/books/${id}`)).status, 400);
  assert.equal((await app.request('/missing')).status, 404);
  const response = await app.request('/books', 'PATCH');
  assert.equal(response.status, 405); assert.equal(response.headers.get('allow'), 'GET, POST');
});

test('records persist after closing and reopening the database', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'books-test-'));
  try {
    const path = join(dir, 'books.sqlite');
    const first = await start(path);
    try { assert.equal((await first.request('/books', 'POST', book)).status, 201); }
    finally { await first.close(); }
    const second = await start(path);
    try { assert.deepEqual(await (await second.request('/books/1')).json(), { id: 1, ...book }); }
    finally { await second.close(); }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});


test('malformed JSON, media types and oversized bodies return JSON errors', async t => {
  const app = await start(); t.after(app.close);
  for (const [body, contentType, status] of [
    ['{', 'application/json', 400],
    ['', 'application/json', 400],
    ['{}', 'text/plain', 415],
    ['x'.repeat(1_048_577), 'application/json', 413],
  ] as const) {
    const response = await app.rawRequest('/books', 'POST', body, contentType);
    assert.equal(response.status, status);
    assert.match(response.headers.get('content-type') ?? '', /application\/json/);
    assert.equal(typeof (await response.json() as { error: string }).error, 'string');
  }
  assert.deepEqual(await (await app.request('/books')).json(), []);
});
