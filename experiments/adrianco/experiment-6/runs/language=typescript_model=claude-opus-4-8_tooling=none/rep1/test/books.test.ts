import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import request from 'supertest';
import { createApp } from '../src/app';
import { createDb, BookRepository } from '../src/db';

function makeApp() {
  const db = createDb(':memory:');
  const repo = new BookRepository(db);
  return createApp(repo);
}

let app: ReturnType<typeof makeApp>;

beforeEach(() => {
  app = makeApp();
});

test('GET /health returns ok', async () => {
  const res = await request(app).get('/health');
  assert.equal(res.status, 200);
  assert.deepEqual(res.body, { status: 'ok' });
});

test('POST /books creates a book and returns 201', async () => {
  const res = await request(app)
    .post('/books')
    .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '978-0441013593' });
  assert.equal(res.status, 201);
  assert.equal(res.body.id, 1);
  assert.equal(res.body.title, 'Dune');
  assert.equal(res.body.author, 'Frank Herbert');
  assert.equal(res.body.year, 1965);
  assert.equal(res.body.isbn, '978-0441013593');
});

test('POST /books rejects missing title and author with 400', async () => {
  const res = await request(app).post('/books').send({ year: 2000 });
  assert.equal(res.status, 400);
  assert.ok(Array.isArray(res.body.errors));
  assert.ok(res.body.errors.some((e: string) => e.includes('title')));
  assert.ok(res.body.errors.some((e: string) => e.includes('author')));
});

test('GET /books lists books and supports ?author= filter', async () => {
  await request(app).post('/books').send({ title: 'A', author: 'Alice' });
  await request(app).post('/books').send({ title: 'B', author: 'Bob' });
  await request(app).post('/books').send({ title: 'C', author: 'Alice' });

  const all = await request(app).get('/books');
  assert.equal(all.status, 200);
  assert.equal(all.body.length, 3);

  const filtered = await request(app).get('/books').query({ author: 'Alice' });
  assert.equal(filtered.status, 200);
  assert.equal(filtered.body.length, 2);
  assert.ok(filtered.body.every((b: { author: string }) => b.author === 'Alice'));
});

test('GET /books/:id returns a single book or 404', async () => {
  await request(app).post('/books').send({ title: 'Solo', author: 'Han' });

  const found = await request(app).get('/books/1');
  assert.equal(found.status, 200);
  assert.equal(found.body.title, 'Solo');

  const missing = await request(app).get('/books/999');
  assert.equal(missing.status, 404);
});

test('PUT /books/:id updates an existing book', async () => {
  await request(app).post('/books').send({ title: 'Old', author: 'Author' });

  const updated = await request(app)
    .put('/books/1')
    .send({ title: 'New', author: 'Author', year: 2024 });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.id, 1);
  assert.equal(updated.body.title, 'New');
  assert.equal(updated.body.year, 2024);

  const missing = await request(app)
    .put('/books/999')
    .send({ title: 'X', author: 'Y' });
  assert.equal(missing.status, 404);
});

test('DELETE /books/:id removes a book', async () => {
  await request(app).post('/books').send({ title: 'Temp', author: 'Author' });

  const del = await request(app).delete('/books/1');
  assert.equal(del.status, 204);

  const after = await request(app).get('/books/1');
  assert.equal(after.status, 404);

  const delMissing = await request(app).delete('/books/1');
  assert.equal(delMissing.status, 404);
});
