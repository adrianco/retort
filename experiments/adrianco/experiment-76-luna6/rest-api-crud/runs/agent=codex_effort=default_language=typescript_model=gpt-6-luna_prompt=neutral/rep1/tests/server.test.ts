import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { createApp } from '../src/server.js';

const db = new DatabaseSync(':memory:');
const app = createApp({ database: db });
let base: string;
before(async () => {
  await new Promise<void>(resolve => app.server.listen(0, '127.0.0.1', resolve));
  const address = app.server.address();
  if (!address || typeof address === 'string') throw new Error('No server address');
  base = `http://127.0.0.1:${address.port}`;
});
after(() => { app.close(); db.close(); });

test('health endpoint returns JSON status', async () => {
  const response = await fetch(`${base}/health`);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'ok' });
});

test('creates, retrieves, filters, updates, and deletes a book', async () => {
  const payload = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' };
  const createdResponse = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json() as { id: string };
  assert.ok(created.id);
  assert.equal((await (await fetch(`${base}/books/${created.id}`)).json() as { title: string }).title, 'Dune');
  assert.equal((await (await fetch(`${base}/books?author=Nobody`)).json() as unknown[]).length, 0);
  const updated = await fetch(`${base}/books/${created.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ...payload, title: 'Dune Messiah' }) });
  assert.equal((await updated.json() as { title: string }).title, 'Dune Messiah');
  assert.equal((await fetch(`${base}/books/${created.id}`, { method: 'DELETE' })).status, 200);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
});

test('rejects invalid required fields and malformed JSON', async () => {
  const missing = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Untitled' }) });
  assert.equal(missing.status, 400);
  const malformed = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{' });
  assert.equal(malformed.status, 400);
});
