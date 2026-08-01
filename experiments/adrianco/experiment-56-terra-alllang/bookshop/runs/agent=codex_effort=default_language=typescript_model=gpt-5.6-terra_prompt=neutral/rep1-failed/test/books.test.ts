import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { createApp } from '../src/app.ts';

async function api() {
  const server = createApp({ databasePath: ':memory:' });
  return async (path: string, init: { method?: string; body?: string } = {}) => {
    const request = Object.assign(Readable.from(init.body ? [init.body] : []), {
      method: init.method ?? 'GET',
      url: path
    });
    let status = 200;
    let body = '';
    const response = {
      writeHead: (code: number) => { status = code; },
      end: (chunk?: string) => { body += chunk ?? ''; }
    };
    server.emit('request', request, response);
    await new Promise(resolve => setImmediate(resolve));
    return { status, json: async () => JSON.parse(body) };
  };
}

test('creates and retrieves a book', async () => {
  const request = await api();
  const created = await request('/books', { method: 'POST', body: JSON.stringify({ title: 'Kindred', author: 'Octavia Butler', year: 1979, isbn: '9780807083697' }) });
  assert.equal(created.status, 201);
  const book = await created.json();
  assert.deepEqual(book, { id: 1, title: 'Kindred', author: 'Octavia Butler', year: 1979, isbn: '9780807083697' });
  const fetched = await request('/books/1');
  assert.equal(fetched.status, 200);
  assert.deepEqual(await fetched.json(), book);
});

test('filters books by author', async () => {
  const request = await api();
  for (const book of [{ title: 'Parable of the Sower', author: 'Octavia Butler' }, { title: 'Dune', author: 'Frank Herbert' }]) {
    await request('/books', { method: 'POST', body: JSON.stringify(book) });
  }
  const result = await request('/books?author=Octavia%20Butler');
  assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), [{ id: 1, title: 'Parable of the Sower', author: 'Octavia Butler', year: null, isbn: null }]);
});

test('validates required fields and supports update/delete', async () => {
  const request = await api();
  const invalid = await request('/books', { method: 'POST', body: JSON.stringify({ title: '' }) });
  assert.equal(invalid.status, 400);
  const created = await request('/books', { method: 'POST', body: JSON.stringify({ title: 'Dune', author: 'Frank Herbert' }) });
  assert.equal(created.status, 201);
  const updated = await request('/books/1', { method: 'PUT', body: JSON.stringify({ year: 1965 }) });
  assert.equal(updated.status, 200);
  assert.equal((await updated.json()).year, 1965);
  const deleted = await request('/books/1', { method: 'DELETE' });
  assert.equal(deleted.status, 204);
  assert.equal((await request('/books/1')).status, 404);
});
