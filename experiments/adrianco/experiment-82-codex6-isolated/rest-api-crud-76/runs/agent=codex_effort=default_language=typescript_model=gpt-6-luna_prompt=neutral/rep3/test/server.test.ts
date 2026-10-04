import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/server.ts';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const dir = mkdtempSync(join(tmpdir(), 'books-api-'));
const app = createApp(join(dir, 'test.sqlite'));
let base = '';
before(async () => {
  await new Promise<void>((resolve) => app.listen(0, '127.0.0.1', resolve));
  const address = app.address();
  if (address && typeof address !== 'string') base = `http://127.0.0.1:${address.port}`;
});
after(async () => {
  app.closeAllConnections();
  await new Promise<void>((resolve, reject) => app.close((err) => err ? reject(err) : resolve()));
  rmSync(dir, { recursive: true, force: true });
});

test('creates, gets, updates, and deletes a book', async () => {
  const createdResponse = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' }) });
  assert.equal(createdResponse.status, 201);
  const created = await createdResponse.json() as { id: number; title: string };
  assert.equal(created.title, 'Dune');
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 200);
  const updated = await fetch(`${base}/books/${created.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Dune Messiah', author: 'Frank Herbert' }) });
  assert.equal(updated.status, 200);
  assert.equal((await updated.json() as { title: string }).title, 'Dune Messiah');
  assert.equal((await fetch(`${base}/books/${created.id}`, { method: 'DELETE' })).status, 204);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
});

test('validates required fields', async () => {
  const response = await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Missing author' }) });
  assert.equal(response.status, 400);
});

test('filters the collection by author and serves health check', async () => {
  await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Book A', author: 'Author A' }) });
  await fetch(`${base}/books`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Book B', author: 'Author B' }) });
  const response = await fetch(`${base}/books?author=Author%20A`);
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json() as Array<{ author: string }>).map((book) => book.author), ['Author A']);
  assert.deepEqual(await (await fetch(`${base}/health`)).json(), { status: 'ok' });
});
