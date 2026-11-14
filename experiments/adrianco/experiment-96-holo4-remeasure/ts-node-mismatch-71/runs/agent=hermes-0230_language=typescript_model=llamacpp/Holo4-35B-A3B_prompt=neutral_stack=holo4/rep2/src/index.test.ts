import request from 'supertest';
import { app } from './index';
import { db } from './database';

afterEach(() => {
  db.prepare('DELETE FROM books').run();
});

describe('GET /health', () => {
  it('returns 200 with status OK', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'OK' });
  });
});

describe('POST /books', () => {
  it('creates a new book and returns 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.title).toBe('The Great Gatsby');
    expect(res.body.author).toBe('F. Scott Fitzgerald');
    expect(res.body.year).toBe(1925);
    expect(res.body.isbn).toBe('978-0743273565');
  });

  it('returns 400 if title or author is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    expect(res.status).toBe(400);
  });
});

describe('GET /books', () => {
  it('lists all books', async () => {
    await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });

    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('filters by author', async () => {
    await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });

    const res = await request(app).get('/books').query({ author: 'F. Scott Fitzgerald' });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe('F. Scott Fitzgerald');
  });
});

describe('GET /books/:id', () => {
  it('returns a book by ID', async () => {
    const bookRes = await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    const id = bookRes.body.id;

    const res = await request(app).get(`/books/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('The Great Gatsby');
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    const bookRes = await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    const id = bookRes.body.id;

    const res = await request(app)
      .put(`/books/${id}`)
      .send({ title: 'The Great Gatsby (Updated)' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('The Great Gatsby (Updated)');
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app).put('/books/9999').send({ title: 'Nope' });
    expect(res.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book', async () => {
    const bookRes = await request(app)
      .post('/books')
      .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
    const id = bookRes.body.id;

    const delRes = await request(app).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
