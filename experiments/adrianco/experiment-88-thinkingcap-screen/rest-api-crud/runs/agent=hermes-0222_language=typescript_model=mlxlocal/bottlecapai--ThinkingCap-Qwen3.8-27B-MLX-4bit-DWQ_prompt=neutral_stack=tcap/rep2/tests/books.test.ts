import { test, describe, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import type express from 'express';
import type { Database } from 'better-sqlite3';
import { createApp } from '../src/app';
import { openDatabase } from '../src/db';
import type { Book } from '../src/validate';

let db: Database;
let app: express.Express;

before(() => {
  db = openDatabase(':memory:');
  app = createApp(db);
});

after(() => {
  db.close();
});

beforeEach(() => {
  db.exec('DELETE FROM books');
});

describe('GET /health', () => {
  test('returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, { status: 'ok' });
  });
});

describe('POST /books', () => {
  test('creates a book with all fields and returns 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
    assert.equal(res.status, 201);
    assert.equal(typeof res.body.id, 'number');
    assert.equal(res.body.title, 'Dune');
    assert.equal(res.body.author, 'Frank Herbert');
    assert.equal(res.body.year, 1965);
    assert.equal(res.body.isbn, '9780441172719');
  });

  test('creates a book with only title and author (year/isbn null)', async () => {
    const res = await request(app).post('/books').send({ title: 'Moby-Dick', author: 'Herman Melville' });
    assert.equal(res.status, 201);
    assert.equal(res.body.title, 'Moby-Dick');
    assert.equal(res.body.author, 'Herman Melville');
    assert.equal(res.body.year, null);
    assert.equal(res.body.isbn, null);
  });

  test('rejects a book without title with 400', async () => {
    const res = await request(app).post('/books').send({ author: 'Someone' });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, 'Validation failed');
    assert.ok(res.body.details.includes('title is required'));
  });

  test('rejects a book without author with 400', async () => {
    const res = await request(app).post('/books').send({ title: 'Orphan' });
    assert.equal(res.status, 400);
    assert.ok(res.body.details.includes('author is required'));
  });

  test('rejects an empty title with 400', async () => {
    const res = await request(app).post('/books').send({ title: '   ', author: 'X' });
    assert.equal(res.status, 400);
  });

  test('rejects a non-integer year with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Bad Year', author: 'X', year: '1999' });
    assert.equal(res.status, 400);
    assert.ok(res.body.details.some((d: string) => d.startsWith('year must be')));
  });

  test('rejects a malformed JSON body with 400', async () => {
    const res = await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send('{"title": "broken"');
    assert.equal(res.status, 400);
  });
});

describe('GET /books', () => {
  test('lists all books', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'One' });
    await request(app).post('/books').send({ title: 'B', author: 'Two' });
    const res = await request(app).get('/books');
    assert.equal(res.status, 200);
    assert.equal(res.body.length, 2);
    const titles = res.body.map((b: Book) => b.title);
    assert.deepEqual(titles, ['A', 'B']);
  });

  test('filters by author (case-insensitive)', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Tolkien' });
    await request(app).post('/books').send({ title: 'B', author: 'Orwell' });
    await request(app).post('/books').send({ title: 'C', author: 'tolkien' });
    const res = await request(app).get('/books').query({ author: 'TOLKIEN' });
    assert.equal(res.status, 200);
    assert.equal(res.body.length, 2);
    assert.ok(res.body.every((b: Book) => b.author.toLowerCase() === 'tolkien'));
  });

  test('returns an empty list when the filter matches nothing', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'One' });
    const res = await request(app).get('/books').query({ author: 'Nobody' });
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, []);
  });
});

describe('GET /books/:id', () => {
  test('returns a single book', async () => {
    const created = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    const res = await request(app).get(`/books/${created.body.id}`);
    assert.equal(res.status, 200);
    assert.equal(res.body.title, 'Dune');
    assert.equal(res.body.author, 'Frank Herbert');
  });

  test('returns 404 for a missing book', async () => {
    const res = await request(app).get('/books/99999');
    assert.equal(res.status, 404);
  });

  test('returns 400 for a non-numeric id', async () => {
    const res = await request(app).get('/books/abc');
    assert.equal(res.status, 400);
  });
});

describe('PUT /books/:id', () => {
  test('updates provided fields and keeps the rest', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Old Title', author: 'Author', year: 1900 });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: 'New Title' });
    assert.equal(res.status, 200);
    assert.equal(res.body.title, 'New Title');
    assert.equal(res.body.author, 'Author');
    assert.equal(res.body.year, 1900);
  });

  test('rejects an update with an empty title with 400', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const res = await request(app).put(`/books/${created.body.id}`).send({ title: '' });
    assert.equal(res.status, 400);
  });

  test('rejects an update with an empty body with 400', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const res = await request(app).put(`/books/${created.body.id}`).send({});
    assert.equal(res.status, 400);
  });

  test('returns 404 for a missing book', async () => {
    const res = await request(app).put('/books/99999').send({ title: 'X' });
    assert.equal(res.status, 404);
  });
});

describe('DELETE /books/:id', () => {
  test('deletes a book (204) and it is gone afterwards', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const del = await request(app).delete(`/books/${created.body.id}`);
    assert.equal(del.status, 204);
    const res = await request(app).get(`/books/${created.body.id}`);
    assert.equal(res.status, 404);
  });

  test('returns 404 for a missing book', async () => {
    const res = await request(app).delete('/books/99999');
    assert.equal(res.status, 404);
  });
});

describe('unknown routes', () => {
  test('returns JSON 404', async () => {
    const res = await request(app).get('/nope');
    assert.equal(res.status, 404);
    assert.deepEqual(res.body, { error: 'Not found' });
  });
});
