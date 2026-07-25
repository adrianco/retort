import request from 'supertest';
import app from '../src/index';
import db from '../src/db';

beforeAll(() => {
  // Ensure clean database
  db.exec('DELETE FROM books');
});

test('health endpoint', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'ok' });
});

test('create, list, get, update, delete book', async () => {
  // create
  const createRes = await request(app)
    .post('/books')
    .send({ title: 'Book A', author: 'Author X', year: 2021, isbn: '123' });
  expect(createRes.status).toBe(201);
  const book = createRes.body;
  expect(book).toHaveProperty('id');
  expect(book.title).toBe('Book A');

  const id = book.id;

  // get single
  const getRes = await request(app).get(`/books/${id}`);
  expect(getRes.status).toBe(200);
  expect(getRes.body.title).toBe('Book A');

  // list with filter
  const listRes = await request(app).get('/books?author=Author X');
  expect(listRes.status).toBe(200);
  expect(Array.isArray(listRes.body)).toBe(true);
  expect(listRes.body.length).toBeGreaterThan(0);

  // update
  const updateRes = await request(app)
    .put(`/books/${id}`)
    .send({ title: 'Book A Updated' });
  expect(updateRes.status).toBe(200);
  expect(updateRes.body.title).toBe('Book A Updated');

  // delete
  const delRes = await request(app).delete(`/books/${id}`);
  expect(delRes.status).toBe(204);

  // confirm deletion
  const getAfterDel = await request(app).get(`/books/${id}`);
  expect(getAfterDel.status).toBe(404);
});

