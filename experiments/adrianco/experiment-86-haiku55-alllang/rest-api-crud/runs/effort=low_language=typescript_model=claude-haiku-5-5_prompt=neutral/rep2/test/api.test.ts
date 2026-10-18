import { after, before, beforeEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import type { Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { openDatabase, type Database } from '../src/db.js';
import { createApp } from '../src/app.js';

let db: Database;
let server: Server;
let base: string;

before(async () => {
  db = openDatabase(':memory:');
  server = createApp(db);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  base = `http://127.0.0.1:${port}`;
});

after(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
  db.close();
});

beforeEach(() => {
  db.exec('DELETE FROM books;');
});

const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

const sample = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' };

async function createBook(body: unknown = sample): Promise<any> {
  const res = await fetch(`${base}/books`, { method: 'POST', ...json(body) });
  assert.equal(res.status, 201);
  return res.json();
}

describe('health', () => {
  it('GET /health returns ok', async () => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201 with the record', async () => {
    const book = await createBook();
    assert.equal(typeof book.id, 'number');
    assert.equal(book.title, 'Dune');
    assert.equal(book.author, 'Frank Herbert');
    assert.equal(book.year, 1965);
    assert.equal(book.isbn, '9780441013593');
  });

  it('accepts a book without optional fields', async () => {
    const book = await createBook({ title: 'Untitled', author: 'Anon' });
    assert.equal(book.year, null);
    assert.equal(book.isbn, null);
  });

  it('rejects missing title and author with 400 and field details', async () => {
    const res = await fetch(`${base}/books`, { method: 'POST', ...json({ year: 2000 }) });
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.ok(body.details.title);
    assert.ok(body.details.author);
  });

  it('rejects an invalid year', async () => {
    const res = await fetch(`${base}/books`, {
      method: 'POST',
      ...json({ title: 'A', author: 'B', year: 'nineteen' }),
    });
    assert.equal(res.status, 400);
    assert.ok((await res.json()).details.year);
  });

  it('rejects malformed JSON with 400', async () => {
    const res = await fetch(`${base}/books`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{not json',
    });
    assert.equal(res.status, 400);
  });
});

describe('GET /books', () => {
  it('lists all books', async () => {
    await createBook();
    await createBook({ title: 'Emma', author: 'Jane Austen' });
    const res = await fetch(`${base}/books`);
    assert.equal(res.status, 200);
    assert.equal((await res.json()).length, 2);
  });

  it('filters by author', async () => {
    await createBook();
    await createBook({ title: 'Emma', author: 'Jane Austen' });
    const res = await fetch(`${base}/books?author=${encodeURIComponent('Jane Austen')}`);
    const books = await res.json();
    assert.equal(books.length, 1);
    assert.equal(books[0].title, 'Emma');
  });

  it('returns an empty array when no books match', async () => {
    const res = await fetch(`${base}/books?author=Nobody`);
    assert.deepEqual(await res.json(), []);
  });
});

describe('GET /books/{id}', () => {
  it('returns a single book', async () => {
    const created = await createBook();
    const res = await fetch(`${base}/books/${created.id}`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), created);
  });

  it('returns 404 for an unknown id', async () => {
    const res = await fetch(`${base}/books/9999`);
    assert.equal(res.status, 404);
  });

  it('returns 400 for a non-numeric id', async () => {
    const res = await fetch(`${base}/books/abc`);
    assert.equal(res.status, 400);
  });
});

describe('PUT /books/{id}', () => {
  it('updates an existing book', async () => {
    const created = await createBook();
    const res = await fetch(`${base}/books/${created.id}`, {
      method: 'PUT',
      ...json({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 }),
    });
    assert.equal(res.status, 200);
    const updated = await res.json();
    assert.equal(updated.id, created.id);
    assert.equal(updated.title, 'Dune Messiah');
    assert.equal(updated.year, 1969);
    assert.equal(updated.isbn, null);
  });

  it('validates the update body', async () => {
    const created = await createBook();
    const res = await fetch(`${base}/books/${created.id}`, {
      method: 'PUT',
      ...json({ title: '', author: 'X' }),
    });
    assert.equal(res.status, 400);
  });

  it('returns 404 for an unknown id', async () => {
    const res = await fetch(`${base}/books/9999`, {
      method: 'PUT',
      ...json({ title: 'T', author: 'A' }),
    });
    assert.equal(res.status, 404);
  });
});

describe('DELETE /books/{id}', () => {
  it('deletes a book and returns 204', async () => {
    const created = await createBook();
    const res = await fetch(`${base}/books/${created.id}`, { method: 'DELETE' });
    assert.equal(res.status, 204);
    const after = await fetch(`${base}/books/${created.id}`);
    assert.equal(after.status, 404);
  });

  it('returns 404 when deleting an unknown id', async () => {
    const res = await fetch(`${base}/books/9999`, { method: 'DELETE' });
    assert.equal(res.status, 404);
  });
});

describe('routing', () => {
  it('returns 404 for unknown routes', async () => {
    const res = await fetch(`${base}/nope`);
    assert.equal(res.status, 404);
  });

  it('returns 405 for unsupported methods on /books', async () => {
    const res = await fetch(`${base}/books`, { method: 'DELETE' });
    assert.equal(res.status, 405);
  });
});
