import request from 'supertest';
import { Express } from 'express';
import { DatabaseSync } from 'node:sqlite';
import { createApp } from '../src/app';
import { createDatabase } from '../src/db';

describe('Book collection API', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    db = createDatabase(':memory:');
    app = createApp(db);
  });

  afterEach(() => {
    db.close();
  });

  test('GET /health returns 200 ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('POST /books creates a book and GET /books/:id retrieves it', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' });

    expect(createRes.status).toBe(201);
    expect(createRes.body).toMatchObject({
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '9780441013593',
    });
    expect(createRes.body.id).toBeDefined();

    const getRes = await request(app).get(`/books/${createRes.body.id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body).toMatchObject({ title: 'Dune', author: 'Frank Herbert' });
  });

  test('POST /books rejects missing title/author', async () => {
    const res = await request(app).post('/books').send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toEqual(
      expect.arrayContaining(['title is required', 'author is required'])
    );
  });

  test('GET /books supports filtering by author', async () => {
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
    await request(app).post('/books').send({ title: 'Book C', author: 'Alice' });

    const res = await request(app).get('/books').query({ author: 'Alice' });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
  });

  test('PUT /books/:id updates a book', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Old Title', author: 'Author X', year: 2000 });
    const id = createRes.body.id;

    const updateRes = await request(app).put(`/books/${id}`).send({ title: 'New Title' });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body).toMatchObject({ title: 'New Title', author: 'Author X', year: 2000 });
  });

  test('PUT /books/:id returns 404 for nonexistent book', async () => {
    const res = await request(app).put('/books/9999').send({ title: 'Whatever' });
    expect(res.status).toBe(404);
  });

  test('DELETE /books/:id removes a book', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'To Delete', author: 'Someone' });
    const id = createRes.body.id;

    const deleteRes = await request(app).delete(`/books/${id}`);
    expect(deleteRes.status).toBe(204);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });

  test('GET /books/:id returns 404 for nonexistent book', async () => {
    const res = await request(app).get('/books/12345');
    expect(res.status).toBe(404);
  });
});
