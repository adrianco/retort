import request from 'supertest';
import { Express } from 'express';
import { DatabaseSync } from 'node:sqlite';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

describe('POST /books', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    db = createDb(':memory:');
    app = createApp(db);
  });

  it('creates a book and returns 201 with the created book', async () => {
    const res = await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });
    expect(res.body.id).toEqual(expect.any(Number));
  });

  it('returns 400 when title is missing', async () => {
    const res = await request(app).post('/books').send({
      author: 'J.R.R. Tolkien',
    });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('returns 400 when author is missing', async () => {
    const res = await request(app).post('/books').send({
      title: 'The Hobbit',
    });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });
});

describe('GET /books', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(async () => {
    db = createDb(':memory:');
    app = createApp(db);

    await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });
    await request(app).post('/books').send({
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '978-0441172719',
    });
  });

  it('returns all books', async () => {
    const res = await request(app).get('/books');

    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('filters books by author', async () => {
    const res = await request(app).get('/books').query({ author: 'Frank Herbert' });

    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0]).toMatchObject({ title: 'Dune', author: 'Frank Herbert' });
  });
});

describe('GET /books/:id', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    db = createDb(':memory:');
    app = createApp(db);
  });

  it('returns a single book by id', async () => {
    const created = await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });

    const res = await request(app).get(`/books/${created.body.id}`);

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
    });
  });

  it('returns 404 when the book does not exist', async () => {
    const res = await request(app).get('/books/999');

    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });
});

describe('PUT /books/:id', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    db = createDb(':memory:');
    app = createApp(db);
  });

  it('updates a book and returns the updated book', async () => {
    const created = await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0261102217',
    });

    const res = await request(app).put(`/books/${created.body.id}`).send({
      title: 'The Hobbit (Revised)',
      author: 'J.R.R. Tolkien',
      year: 1951,
      isbn: '978-0261102217',
    });

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: 'The Hobbit (Revised)',
      year: 1951,
    });
  });

  it('returns 400 when title is missing', async () => {
    const created = await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
    });

    const res = await request(app).put(`/books/${created.body.id}`).send({
      author: 'J.R.R. Tolkien',
    });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('returns 404 when the book does not exist', async () => {
    const res = await request(app).put('/books/999').send({
      title: 'Title',
      author: 'Author',
    });

    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });
});

describe('DELETE /books/:id', () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    db = createDb(':memory:');
    app = createApp(db);
  });

  it('deletes a book and returns 204', async () => {
    const created = await request(app).post('/books').send({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
    });

    const res = await request(app).delete(`/books/${created.body.id}`);

    expect(res.status).toBe(204);

    const getRes = await request(app).get(`/books/${created.body.id}`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 when the book does not exist', async () => {
    const res = await request(app).delete('/books/999');

    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });
});
