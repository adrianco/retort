import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import type { AddressInfo } from 'node:net';
import type { Server } from 'node:http';
import { BookRepository } from '../src/db.js';
import { createApp } from '../src/app.js';

let server: Server;
let repo: BookRepository;
let base: string;

before(async () => {
  repo = new BookRepository(':memory:');
  server = createApp(repo);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  base = `http://127.0.0.1:${port}`;
});

after(async () => {
  await new Promise((resolve) => server.close(resolve));
  repo.close();
});

const json = (method: string, body?: unknown) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

const sample = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' };

describe('health', () => {
  test('GET /health reports ok', async () => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: 'ok', database: 'up' });
  });
});

describe('books CRUD', () => {
  test('POST creates a book and returns 201', async () => {
    const res = await fetch(`${base}/books`, json('POST', sample));
    assert.equal(res.status, 201);
    const book = await res.json();
    assert.equal(book.title, 'Dune');
    assert.equal(book.author, 'Frank Herbert');
    assert.equal(book.year, 1965);
    assert.equal(book.isbn, '9780441013593');
    assert.equal(typeof book.id, 'number');
  });

  test('GET /books/{id} returns the book, 404 when missing', async () => {
    const created = await (await fetch(`${base}/books`, json('POST', { title: 'Emma', author: 'Jane Austen' }))).json();
    const res = await fetch(`${base}/books/${created.id}`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: created.id, title: 'Emma', author: 'Jane Austen', year: null, isbn: null });

    const missing = await fetch(`${base}/books/999999`);
    assert.equal(missing.status, 404);
    assert.equal((await missing.json()).error, 'Book not found');
  });

  test('GET /books lists all books and filters by author', async () => {
    await fetch(`${base}/books`, json('POST', { title: 'Children of Dune', author: 'Frank Herbert' }));
    const all = await (await fetch(`${base}/books`)).json();
    assert.ok(all.length >= 3);

    const filtered = await (await fetch(`${base}/books?author=Frank%20Herbert`)).json();
    assert.ok(filtered.length >= 2);
    assert.ok(filtered.every((b: { author: string }) => b.author === 'Frank Herbert'));

    const none = await (await fetch(`${base}/books?author=Nobody`)).json();
    assert.deepEqual(none, []);
  });

  test('PUT updates a book and returns it; 404 when missing', async () => {
    const created = await (await fetch(`${base}/books`, json('POST', sample))).json();
    const res = await fetch(`${base}/books/${created.id}`, json('PUT', { title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 }));
    assert.equal(res.status, 200);
    const updated = await res.json();
    assert.equal(updated.id, created.id);
    assert.equal(updated.title, 'Dune Messiah');
    assert.equal(updated.year, 1969);
    assert.equal(updated.isbn, null);

    const missing = await fetch(`${base}/books/999999`, json('PUT', sample));
    assert.equal(missing.status, 404);
  });

  test('DELETE removes a book with 204; second delete is 404', async () => {
    const created = await (await fetch(`${base}/books`, json('POST', sample))).json();
    const res = await fetch(`${base}/books/${created.id}`, json('DELETE'));
    assert.equal(res.status, 204);
    assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
    assert.equal((await fetch(`${base}/books/${created.id}`, json('DELETE'))).status, 404);
  });
});

describe('validation', () => {
  test('POST rejects missing title and author with 400 details', async () => {
    const res = await fetch(`${base}/books`, json('POST', { year: 2000 }));
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.equal(body.error, 'Validation failed');
    assert.ok(body.details.title);
    assert.ok(body.details.author);
  });

  test('blank strings are rejected', async () => {
    const res = await fetch(`${base}/books`, json('POST', { title: '   ', author: 'X' }));
    assert.equal(res.status, 400);
    assert.ok((await res.json()).details.title);
  });

  test('non-integer year is rejected', async () => {
    const res = await fetch(`${base}/books`, json('POST', { title: 'T', author: 'A', year: 'abc' }));
    assert.equal(res.status, 400);
    assert.ok((await res.json()).details.year);
  });

  test('malformed JSON returns 400', async () => {
    const res = await fetch(`${base}/books`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{bad' });
    assert.equal(res.status, 400);
    assert.equal((await res.json()).error, 'Malformed JSON body');
  });

  test('invalid id and unknown routes return 404; wrong method returns 405', async () => {
    assert.equal((await fetch(`${base}/books/abc`)).status, 404);
    assert.equal((await fetch(`${base}/nope`)).status, 404);
    const res = await fetch(`${base}/books/1`, json('POST', sample));
    assert.equal(res.status, 405);
  });
});
