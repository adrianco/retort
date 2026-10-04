import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { createApp } from '../src/app.js';

const app = createApp(new DatabaseSync(':memory:'));
let base: string;
before(async () => {
  await new Promise<void>(resolve => app.listen(0, '127.0.0.1', resolve));
  const address = app.address();
  if (!address || typeof address === 'string') throw new Error('Server failed to start');
  base = `http://127.0.0.1:${address.port}`;
});
after(async () => { await new Promise<void>(resolve => app.close(() => resolve())); });

test('health check responds with JSON', async () => {
  const response = await fetch(`${base}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'ok' });
});

test('creates, retrieves, filters, updates, and deletes books', async () => {
  const createdResponse = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' }) });
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json() as { id: string; title: string };
  assert.equal(created.title, 'Dune');
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 200);
  const filtered = await fetch(`${base}/books?author=Frank%20Herbert`);
  assert.equal((await filtered.json() as unknown[]).length, 1);
  const updated = await fetch(`${base}/books/${created.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune Messiah', author: 'Frank Herbert' }) });
  assert.equal((await updated.json() as { title: string }).title, 'Dune Messiah');
  assert.equal((await fetch(`${base}/books/${created.id}`, { method: 'DELETE' })).status, 204);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
});

test('rejects missing required fields and reports unknown books', async () => {
  const invalid = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'No author' }) });
  assert.equal(invalid.status, 400);
  assert.equal((await fetch(`${base}/books/no-such-book`)).status, 404);
});
