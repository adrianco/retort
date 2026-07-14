import request from 'supertest';
import { createApp } from './app';
import { createDb } from './db';

function makeApp() {
  // Use in-memory SQLite for tests
  const db = createDb(':memory:');
  return { app: createApp(db), db };
}

describe('GET /health', () => {
  it('returns 200 with status ok', async () => {
    const { app } = makeApp();
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201', async () => {
    const { app } = makeApp();
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '978-0-441-17271-9' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '978-0-441-17271-9',
    });
  });

  it('returns 400 when title is missing', async () => {
    const { app } = makeApp();
    const res = await request(app).post('/books').send({ author: 'Someone' });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('returns 400 when author is missing', async () => {
    const { app } = makeApp();
    const res = await request(app).post('/books').send({ title: 'A Book' });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });
});

describe('GET /books', () => {
  it('returns all books', async () => {
    const { app } = makeApp();
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('filters books by author', async () => {
    const { app } = makeApp();
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
    const res = await request(app).get('/books?author=Alice');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe('Alice');
  });
});

describe('GET /books/:id', () => {
  it('returns a single book', async () => {
    const { app } = makeApp();
    const created = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    const id = created.body.id;
    const res = await request(app).get(`/books/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Dune');
  });

  it('returns 404 for unknown id', async () => {
    const { app } = makeApp();
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    const { app } = makeApp();
    const created = await request(app).post('/books').send({ title: 'Old Title', author: 'Author' });
    const id = created.body.id;
    const res = await request(app).put(`/books/${id}`).send({ title: 'New Title' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Author');
  });

  it('returns 404 for unknown id', async () => {
    const { app } = makeApp();
    const res = await request(app).put('/books/9999').send({ title: 'X', author: 'Y' });
    expect(res.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204', async () => {
    const { app } = makeApp();
    const created = await request(app).post('/books').send({ title: 'To Delete', author: 'Author' });
    const id = created.body.id;
    const res = await request(app).delete(`/books/${id}`);
    expect(res.status).toBe(204);
    const check = await request(app).get(`/books/${id}`);
    expect(check.status).toBe(404);
  });

  it('returns 404 for unknown id', async () => {
    const { app } = makeApp();
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
