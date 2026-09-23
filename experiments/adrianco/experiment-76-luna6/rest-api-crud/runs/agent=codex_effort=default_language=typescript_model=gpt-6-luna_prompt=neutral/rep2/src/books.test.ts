import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { Readable, Writable } from 'node:stream';
import { IncomingMessage, ServerResponse } from 'node:http';
import { createBookServer } from './books';

const app = createBookServer(':memory:');
after(() => app.close());

async function request(path: string, method = 'GET', body?: unknown) {
  const chunks = body === undefined ? [] : [Buffer.from(JSON.stringify(body))];
  const incoming = Readable.from(chunks) as IncomingMessage;
  incoming.method = method;
  incoming.url = path;
  let status = 200;
  let responseBody = '';
  const outgoing = new Writable({ write(chunk, _encoding, callback) { responseBody += chunk.toString(); callback(); } }) as ServerResponse;
  outgoing.writeHead = ((code: number) => { status = code; return outgoing; }) as ServerResponse['writeHead'];
  outgoing.end = ((chunk?: any) => { if (chunk) responseBody += chunk.toString(); return outgoing; }) as ServerResponse['end'];
  app.server.emit('request', incoming, outgoing);
  await new Promise((resolve) => setImmediate(resolve));
  return { status, body: JSON.parse(responseBody) as any };
}

test('health endpoint reports service status', async () => {
  assert.deepEqual(await request('/health'), { status: 200, body: { status: 'ok' } });
});

test('creates a book, retrieves it, and filters by author', async () => {
  const created = await request('/books', 'POST', { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
  assert.equal(created.status, 201);
  assert.equal(created.body.title, 'Dune');
  const got = await request(`/books/${created.body.id}`);
  assert.deepEqual(got.body, created.body);
  const filtered = await request('/books?author=frank%20herbert');
  assert.equal(filtered.status, 200);
  assert.deepEqual(filtered.body.map((book: any) => book.id), [created.body.id]);
});

test('validates required fields and returns 404 for missing books', async () => {
  const invalid = await request('/books', 'POST', { title: 'Missing author' });
  assert.equal(invalid.status, 400);
  assert.match(invalid.body.error, /author is required/);
  assert.equal((await request('/books/999999')).status, 404);
});

test('updates and deletes a book', async () => {
  const created = await request('/books', 'POST', { title: 'Old', author: 'Writer' });
  const updated = await request(`/books/${created.body.id}`, 'PUT', { title: 'New', author: 'Writer', year: 2020 });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.title, 'New');
  assert.equal(updated.body.year, 2020);
  assert.equal((await request(`/books/${created.body.id}`, 'DELETE')).status, 200);
  assert.equal((await request(`/books/${created.body.id}`)).status, 404);
});
