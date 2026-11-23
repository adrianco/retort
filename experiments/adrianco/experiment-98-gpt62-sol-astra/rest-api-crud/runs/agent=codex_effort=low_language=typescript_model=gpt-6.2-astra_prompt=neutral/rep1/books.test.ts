import test, { type TestContext } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { openCollection } from './books.js';

function client(t: TestContext, path = ':memory:') {
  const api = openCollection(path);
  t.after(api.close);
  return (method: string, route: string, body?: unknown) => api.handle(
    new Request('http://localhost' + route, { method, body: JSON.stringify(body) })
  );
}

const book = { title: 'Kindred', author: 'Octavia Butler', year: 1979, isbn: '0123456789' };

test('create, read, replace and delete a book', async t => {
  const call = client(t);
  const created = await call('POST', '/books', book);
  assert.equal(created.status, 201);
  const saved = await created.json();
  assert.deepEqual(saved, { ...book, id: 1 });
  const route = created.headers.get('location')!;
  assert.deepEqual(await (await call('GET', route)).json(), saved);
  const replacement = { title: 'Dawn', author: book.author };
  const updated = await call('PUT', route, replacement);
  assert.equal(updated.status, 200);
  assert.deepEqual(await updated.json(), { ...replacement, id: saved.id, year: null, isbn: null });
  assert.equal((await call('DELETE', route)).status, 204);
  for (const method of ['GET', 'PUT', 'DELETE']) {
    assert.equal((await call(method, route, method === 'PUT' ? replacement : undefined)).status, 404);
  }
});

test('lists all books or filters by exact author', async t => {
  const call = client(t);
  const first = await (await call('POST', '/books', book)).json();
  const second = await (await call('POST', '/books', { ...book, author: 'Other' })).json();
  assert.deepEqual(await (await call('GET', '/books')).json(), [first, second]);
  assert.deepEqual(await (await call('GET', '/books?author=Octavia%20Butler')).json(), [first]);
  assert.deepEqual(await (await call('GET', '/books?author=Nobody')).json(), []);
});

test('rejects invalid input without changing stored books', async t => {
  const call = client(t);
  const saved = await (await call('POST', '/books', book)).json();
  for (const input of [null, [], { author: 'A' }, { title: 'T' }, { ...book, title: '  ' },
    { ...book, author: 3 }, { ...book, year: 0.5 }, { ...book, isbn: 123 }]) {
    assert.equal((await call('POST', '/books', input)).status, 400);
    assert.equal((await call('PUT', '/books/1', input)).status, 400);
  }
  assert.deepEqual(await (await call('GET', '/books')).json(), [saved]);
});

test('returns JSON for health and malformed JSON requests', async t => {
  const api = openCollection(':memory:');
  t.after(api.close);
  const health = await api.handle(new Request('http://localhost/health'));
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { status: 'ok' });
  const bad = await api.handle(new Request('http://localhost/books', { method: 'POST', body: '{' }));
  assert.equal(bad.status, 400);
  assert.deepEqual(await bad.json(), { error: 'Invalid JSON' });
});

test('books survive closing and reopening the database', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'books-'));
  const path = join(dir, 'collection.sqlite');
  try {
    const first = openCollection(path);
    try {
      await first.handle(new Request('http://localhost/books', { method: 'POST', body: JSON.stringify(book) }));
    } finally {
      first.close();
    }
    const second = openCollection(path);
    try {
      const read = await second.handle(new Request('http://localhost/books/1'));
      assert.deepEqual(await read.json(), { ...book, id: 1 });
    } finally {
      second.close();
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
