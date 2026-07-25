import request from 'supertest';
import app from './index';
import { getDb } from './database';

// Before tests, clear the database
beforeAll(async () => {
  const db = await getDb('./test-books.db');
  await db.exec('DROP TABLE IF EXISTS books;');
  await db.exec(`CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  );`);
});

test('health endpoint returns ok', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'ok' });
});

test('create book validates required fields', async () => {
  const res = await request(app).post('/books').send({ title: 'Test' });
  expect(res.status).toBe(400);
  expect(res.body).toHaveProperty('error');
});

test('full CRUD flow', async () => {
  // Create
  const createRes = await request(app)
    .post('/books')
    .send({ title: 'Book', author: 'Author', year: 2020, isbn: '123' });
  expect(createRes.status).toBe(201);
  const created = createRes.body;
  expect(created).toHaveProperty('id');
  expect(created.title).toBe('Book');

  const id = created.id;

  // Get single
  const getRes = await request(app).get(`/books/${id}`);
  expect(getRes.status).toBe(200);
  expect(getRes.body.title).toBe('Book');

  // List
  const listRes = await request(app).get('/books');
  expect(listRes.status).toBe(200);
  expect(Array.isArray(listRes.body)).toBe(true);
  expect(listRes.body.length).toBeGreaterThan(0);

  // Update
  const updRes = await request(app)
    .put(`/books/${id}`)
    .send({ title: 'Updated', author: 'Author', year: 2021, isbn: '456' });
  expect(updRes.status).toBe(200);
  expect(updRes.body.title).toBe('Updated');

  // Delete
  const delRes = await request(app).delete(`/books/${id}`);
  expect(delRes.status).toBe(204);

  // Verify deleted
  const afterDel = await request(app).get(`/books/${id}`);
  expect(afterDel.status).toBe(404);
});
