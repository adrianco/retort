import request from 'supertest';
import app from '../index';
import { initDb, db } from '../database';

beforeAll(async () => {
  await initDb();
});

beforeEach(async () => {
  // clear table
  await db.run('DELETE FROM books');
});

afterAll(() => {
  db.close();
});

test('POST /books creates a book', async () => {
  const res = await request(app)
    .post('/books')
    .send({ title: 'Test Book', author: 'Author', year: 2020, isbn: '123' });
  expect(res.status).toBe(201);
  expect(res.body).toMatchObject({ title: 'Test Book', author: 'Author', year: 2020, isbn: '123' });
  expect(res.body.id).toBeDefined();
});

test('GET /books returns list', async () => {
  await request(app).post('/books').send({ title: 'A', author: 'B' });
  const res = await request(app).get('/books');
  expect(res.status).toBe(200);
  expect(res.body.length).toBe(1);
});

test('GET /books?author= filters', async () => {
  await request(app).post('/books').send({ title: 'X', author: 'Same' });
  await request(app).post('/books').send({ title: 'Y', author: 'Other' });
  const res = await request(app).get('/books').query({ author: 'Same' });
  expect(res.body.length).toBe(1);
  expect(res.body[0].author).toBe('Same');
});

test('PUT /books/:id updates', async () => {
  const create = await request(app).post('/books').send({ title: 'Old', author: 'A' });
  const id = create.body.id;
  const upd = await request(app).put(`/books/${id}`).send({ title: 'New' });
  expect(upd.body.title).toBe('New');
  expect(upd.body.author).toBe('A');
});

test('DELETE /books/:id deletes', async () => {
  const create = await request(app).post('/books').send({ title: 'ToDelete', author: 'A' });
  const id = create.body.id;
  const del = await request(app).delete(`/books/${id}`);
  expect(del.status).toBe(204);
  const get = await request(app).get(`/books/${id}`);
  expect(get.status).toBe(404);
});

test('health check', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'ok' });
});

