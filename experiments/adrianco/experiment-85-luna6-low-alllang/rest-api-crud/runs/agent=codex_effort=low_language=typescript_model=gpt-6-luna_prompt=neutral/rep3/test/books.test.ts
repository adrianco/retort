import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { BookStore } from '../src/books.js';
import { createApp } from '../src/server.js';

const directory = mkdtempSync(join(tmpdir(), 'books-api-'));
const store = new BookStore(join(directory, 'test.sqlite'));
const server = createApp(store);
let base: string;

before(async () => {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (address && typeof address !== 'string') base = `http://127.0.0.1:${address.port}`;
});
after(async () => {
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  store.close();
  rmSync(directory, { recursive: true, force: true });
});

test('health check responds with JSON status', async () => {
  const response = await fetch(`${base}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'ok' });
});

test('creates, fetches, filters, updates, and deletes books', async () => {
  const createdResponse = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' }) });
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json() as { id: number };
  assert.equal((await (await fetch(`${base}/books/${created.id}`)).json() as { title: string }).title, 'Dune');
  assert.equal((await (await fetch(`${base}/books?author=Frank%20Herbert`)).json() as unknown[]).length, 1);
  const updated = await fetch(`${base}/books/${created.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune Messiah', author: 'Frank Herbert' }) });
  assert.equal((await updated.json() as { title: string }).title, 'Dune Messiah');
  assert.equal((await fetch(`${base}/books/${created.id}`, { method: 'DELETE' })).status, 200);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
});

test('rejects missing required fields and reports missing books', async () => {
  const invalid = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'No author' }) });
  assert.equal(invalid.status, 400);
  assert.match((await invalid.json() as { error: string }).error, /author is required/);
  assert.equal((await fetch(`${base}/books/9999`)).status, 404);
});
