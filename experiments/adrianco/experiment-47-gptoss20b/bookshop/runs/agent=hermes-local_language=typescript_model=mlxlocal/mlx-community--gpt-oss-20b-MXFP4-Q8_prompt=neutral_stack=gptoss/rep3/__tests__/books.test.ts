import request from 'supertest';
import fs from 'fs';
import path from 'path';
import app from '../src/index';

const dbPath = path.join(__dirname, '..', 'data', 'books.db');

beforeAll(() => {
  // Ensure fresh db
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }
});

afterAll(() => {
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }
});

test('health endpoint returns ok', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'ok' });
});

test('create, list, get, update, delete book', async () => {
  // create
  const createRes = await request(app).post('/books').send({ title: 'Book1', author: 'Author1', year: 2020, isbn: '123' });
  expect(createRes.status).toBe(201);
  const id = createRes.body.id;
  expect(id).toBeDefined();

  // list
  const listRes = await request(app).get('/books');
  expect(listRes.status).toBe(200);
  expect(listRes.body).toHaveLength(1);
  expect(listRes.body[0]).toMatchObject({ id, title: 'Book1', author: 'Author1', year: 2020, isbn: '123' });

  // get by id
  const getRes = await request(app).get(`/books/${id}`);
  expect(getRes.status).toBe(200);
  expect(getRes.body).toMatchObject({ id, title: 'Book1', author: 'Author1', year: 2020, isbn: '123' });

  // update
  const updRes = await request(app).put(`/books/${id}`).send({ title: 'Book1 Updated', year: 2021 });
  expect(updRes.status).toBe(200);
  expect(updRes.body).toMatchObject({ id, title: 'Book1 Updated', author: 'Author1', year: 2021, isbn: '123' });

  // delete
  const delRes = await request(app).delete(`/books/${id}`);
  expect(delRes.status).toBe(204);

  // ensure deleted
  const getAfterDel = await request(app).get(`/books/${id}`);
  expect(getAfterDel.status).toBe(404);
});

 test('author filter works', async () => {
  // create two books
  await request(app).post('/books').send({ title: 'A', author: 'X', year: 2000 });
  await request(app).post('/books').send({ title: 'B', author: 'Y', year: 2001 });
  const res = await request(app).get('/books?author=Y');
  expect(res.status).toBe(200);
  expect(res.body).toHaveLength(1);
  expect(res.body[0].author).toBe('Y');
 });

 test('validation rejects missing title', async () => {
  const res = await request(app).post('/books').send({ author: 'A' });
  expect(res.status).toBe(400);
  expect(res.body.errors).toBeDefined();
 });
