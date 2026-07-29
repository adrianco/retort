import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { BookRepository } from '../src/database.ts';
import { parseBook } from '../src/app.ts';

function repository(): BookRepository { return new BookRepository(new DatabaseSync(':memory:')); }

test('creates and retrieves a book', () => {
  const books = repository();
  const created = books.create({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
  assert.equal(created.id, 1);
  assert.deepEqual(books.find(created.id), created);
  books.close();
});

test('lists books with a case-insensitive author filter', () => {
  const books = repository();
  books.create({ title: 'Dune', author: 'Frank Herbert' });
  books.create({ title: 'Foundation', author: 'Isaac Asimov' });
  assert.deepEqual(books.list('herbert').map((book) => book.title), ['Dune']);
  assert.equal(books.list().length, 2);
  books.close();
});

test('updates and deletes books, returning null/false for missing IDs', () => {
  const books = repository();
  const created = books.create({ title: 'Old title', author: 'Author' });
  assert.equal(books.update(created.id, { title: 'New title', author: 'Author' })?.title, 'New title');
  assert.equal(books.delete(created.id), true);
  assert.equal(books.find(created.id), null);
  assert.equal(books.delete(created.id), false);
  assert.equal(books.update(created.id, { title: 'Missing', author: 'Author' }), null);
  books.close();
});

test('requires title and author during input validation', () => {
  assert.equal(parseBook({ author: 'Author' }).error, 'title is required');
  assert.equal(parseBook({ title: 'Title' }).error, 'author is required');
  assert.equal(parseBook({ title: ' Title ', author: ' Author ' }).value?.title, 'Title');
});
