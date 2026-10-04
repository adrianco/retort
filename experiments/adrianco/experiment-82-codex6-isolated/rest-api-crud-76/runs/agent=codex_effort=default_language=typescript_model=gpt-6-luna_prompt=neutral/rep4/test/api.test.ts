import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/server.js';
import { BookStore } from '../src/books.js';

const store = new BookStore(':memory:');
const { server } = createApp(store);
let base = '';
before(async () => {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (address && typeof address === 'object') base = `http://127.0.0.1:${address.port}`;
});
after(async () => {
  await new Promise<void>(resolve => server.close(() => resolve()));
  store.close();
});

test('health check responds with JSON status', async () => {
  const response = await fetch(`${base}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'ok' });
});

test('creates books, filters by author, gets by ID, and updates', async () => {
  const created = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' }) });
  assert.equal(created.status, 201);
  const book = await created.json() as { id: number; title: string };
  assert.equal(book.title, 'Dune');
  const filtered = await fetch(`${base}/books?author=Frank%20Herbert`);
  assert.equal((await filtered.json() as unknown[]).length, 1);
  const fetched = await fetch(`${base}/books/${book.id}`);
  assert.equal(fetched.status, 200);
  const updated = await fetch(`${base}/books/${book.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune Messiah', author: 'Frank Herbert' }) });
  assert.equal((await updated.json() as { title: string }).title, 'Dune Messiah');
});

test('validates required fields and deletes books', async () => {
  const invalid = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Missing author' }) });
  assert.equal(invalid.status, 400);
  const created = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Test', author: 'Author' }) });
  const book = await created.json() as { id: number };
  const removed = await fetch(`${base}/books/${book.id}`, { method: 'DELETE' });
  assert.equal(removed.status, 200);
  assert.equal((await fetch(`${base}/books/${book.id}`)).status, 404);
});
