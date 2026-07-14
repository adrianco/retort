import request from 'supertest';
import { createApp } from '../app';
import { createDb } from '../db';

function createTestApp() {
  const db = createDb(':memory:');
  return { app: createApp(db), db };
}

describe('GET /health', () => {
  it('returns 200 with ok status', async () => {
    const { app } = createTestApp();
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201', async () => {
    const { app } = createTestApp();
    const res = await request(app)
      .post('/books')
      .send({ title: 'Clean Code', author: 'Robert Martin', year: 2008, isbn: '978-0132350884' });
    expect(res.status).toBe(201);
    expect(res.body.id).toBeDefined();
    expect(res.body.title).toBe('Clean Code');
    expect(res.body.author).toBe('Robert Martin');
    expect(res.body.year).toBe(2008);
    expect(res.body.isbn).toBe('978-0132350884');
  });

  it('returns 400 when title is missing', async () => {
    const { app } = createTestApp();
    const res = await request(app)
      .post('/books')
      .send({ author: 'Robert Martin' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/i);
  });

  it('returns 400 when author is missing', async () => {
    const { app } = createTestApp();
    const res = await request(app)
      .post('/books')
      .send({ title: 'Clean Code' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/author/i);
  });

  it('returns 400 when title is empty string', async () => {
    const { app } = createTestApp();
    const res = await request(app)
      .post('/books')
      .send({ title: '   ', author: 'Robert Martin' });
    expect(res.status).toBe(400);
  });
});

describe('GET /books', () => {
  it('returns empty array when no books', async () => {
    const { app } = createTestApp();
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it('returns all books', async () => {
    const { app } = createTestApp();
    await request(app).post('/books').send({ title: 'Book A', author: 'Author A' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Author B' });
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('filters by author query param', async () => {
    const { app } = createTestApp();
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
    const res = await request(app).get('/books?author=Alice');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe('Alice');
  });
});

describe('GET /books/:id', () => {
  it('returns the book by id', async () => {
    const { app } = createTestApp();
    const createRes = await request(app).post('/books').send({ title: 'Clean Code', author: 'Robert Martin' });
    const id = createRes.body.id;
    const res = await request(app).get(`/books/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(id);
    expect(res.body.title).toBe('Clean Code');
  });

  it('returns 404 for unknown id', async () => {
    const { app } = createTestApp();
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
    expect(res.body.error).toMatch(/not found/i);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    const { app } = createTestApp();
    const createRes = await request(app).post('/books').send({ title: 'Old Title', author: 'Author' });
    const id = createRes.body.id;
    const res = await request(app).put(`/books/${id}`).send({ title: 'New Title' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Author');
  });

  it('returns 404 for unknown id', async () => {
    const { app } = createTestApp();
    const res = await request(app).put('/books/9999').send({ title: 'X' });
    expect(res.status).toBe(404);
  });

  it('returns 400 when title is empty string', async () => {
    const { app } = createTestApp();
    const createRes = await request(app).post('/books').send({ title: 'Title', author: 'Author' });
    const id = createRes.body.id;
    const res = await request(app).put(`/books/${id}`).send({ title: '' });
    expect(res.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204', async () => {
    const { app } = createTestApp();
    const createRes = await request(app).post('/books').send({ title: 'To Delete', author: 'Author' });
    const id = createRes.body.id;
    const res = await request(app).delete(`/books/${id}`);
    expect(res.status).toBe(204);
    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 for unknown id', async () => {
    const { app } = createTestApp();
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
