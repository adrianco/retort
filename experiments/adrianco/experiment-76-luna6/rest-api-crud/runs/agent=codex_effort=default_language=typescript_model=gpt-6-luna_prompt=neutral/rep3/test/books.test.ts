import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createBookStore, validateBook } from '../src/server.ts';

async function withStore(run: (store: ReturnType<typeof createBookStore>) => void): Promise<void> {
  const dir = await mkdtemp(join(tmpdir(), 'books-api-'));
  const store = createBookStore(join(dir, 'test.sqlite'));
  try { run(store); }
  finally { store.close(); await rm(dir, { recursive: true, force: true }); }
}

test('validates required fields and normalizes optional book data', () => {
  assert.equal(validateBook({ title: 'Dune' }).error, 'author is required');
  assert.equal(validateBook({ author: 'Frank Herbert' }).error, 'title is required');
  assert.deepEqual(validateBook({ title: ' Dune ', author: 'Frank Herbert', year: 1965 }).value,
    { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: null });
});

test('creates and retrieves a book from SQLite', async () => withStore((store) => {
  const created = store.create({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: null });
  assert.equal(created.id, 1);
  assert.deepEqual(store.get(created.id), created);
}));

test('lists books with an exact author filter', async () => withStore((store) => {
  store.create({ title: 'Dune', author: 'Frank Herbert', year: null, isbn: null });
  store.create({ title: 'The Hobbit', author: 'J.R.R. Tolkien', year: null, isbn: null });
  assert.equal(store.list().length, 2);
  assert.deepEqual(store.list('Frank Herbert').map((book) => book.title), ['Dune']);
}));

test('updates and deletes books, returning no result for missing IDs', async () => withStore((store) => {
  const created = store.create({ title: 'Dune', author: 'Frank Herbert', year: null, isbn: null });
  assert.equal(store.update(created.id, { title: 'Dune Messiah', author: 'Frank Herbert', year: 1969, isbn: null })?.title, 'Dune Messiah');
  assert.equal(store.update(999, { title: 'Missing', author: 'Nobody', year: null, isbn: null }), undefined);
  assert.equal(store.delete(created.id), true);
  assert.equal(store.delete(created.id), false);
}));
