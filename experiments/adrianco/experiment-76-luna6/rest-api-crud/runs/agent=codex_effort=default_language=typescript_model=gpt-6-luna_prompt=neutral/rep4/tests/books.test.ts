import { afterEach, beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { createHandler } from '../src/app.ts';

let db: DatabaseSync;
let handle: ReturnType<typeof createHandler>;

beforeEach(() => {
  db = new DatabaseSync(':memory:');
  db.exec('CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)');
  handle = createHandler(db);
});
afterEach(() => db.close());

async function call(method: string, path: string, body?: unknown) {
  const req = {
    method,
    url: path,
    async *[Symbol.asyncIterator]() {
      if (body !== undefined) yield Buffer.from(typeof body === 'string' ? body : JSON.stringify(body));
    },
  } as IncomingMessage;
  const headers: Record<string, string> = {};
  let responseBody = '';
  const res = {
    statusCode: 200,
    setHeader(name: string, value: string) { headers[name] = value; return this; },
    end(value?: string) { responseBody = value ?? ''; return this; },
  } as unknown as ServerResponse;
  await handle(req, res);
  return {
    status: res.statusCode,
    headers,
    body: responseBody ? JSON.parse(responseBody) as any : undefined,
  };
}

test('creates and retrieves a book', async () => {
  const created = await call('POST', '/books', { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
  assert.equal(created.status, 201);
  assert.equal(created.body.title, 'Dune');
  assert.equal((await call('GET', `/books/${created.body.id}`)).body.author, 'Frank Herbert');
});

test('validates required title and author', async () => {
  assert.equal((await call('POST', '/books', { title: 'No author' })).status, 400);
  assert.equal((await call('POST', '/books', { author: 'Someone' })).status, 400);
});

test('filters by author and supports update and delete', async () => {
  const created = await call('POST', '/books', { title: 'Foundation', author: 'Isaac Asimov' });
  const id = created.body.id;
  assert.equal((await call('GET', '/books?author=isaac%20asimov')).body.length, 1);
  const updated = await call('PUT', `/books/${id}`, { title: 'Foundation and Empire', author: 'Isaac Asimov', year: 1952 });
  assert.equal(updated.body.title, 'Foundation and Empire');
  assert.equal((await call('DELETE', `/books/${id}`)).status, 204);
  assert.equal((await call('GET', `/books/${id}`)).status, 404);
});

test('returns health status', async () => {
  const response = await call('GET', '/health');
  assert.equal(response.status, 200);
  assert.deepEqual(response.body, { status: 'ok' });
});
