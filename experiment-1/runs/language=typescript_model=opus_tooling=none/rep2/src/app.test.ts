import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { createApp } from './app';
import { createDb } from './db';

function makeApp() {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Book API', () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    app = makeApp();
  });

  it('GET /health returns ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('POST /books requires title and author', async () => {
    const r1 = await request(app).post('/books').send({ author: 'A' });
    expect(r1.status).toBe(400);
    const r2 = await request(app).post('/books').send({ title: 'T' });
    expect(r2.status).toBe(400);
  });

  it('POST /books creates a book and returns 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Herbert', year: 1965, isbn: '123' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: 1,
      title: 'Dune',
      author: 'Herbert',
      year: 1965,
      isbn: '123',
    });
  });

  it('GET /books lists books and filters by author', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'X' });
    await request(app).post('/books').send({ title: 'B', author: 'Y' });
    await request(app).post('/books').send({ title: 'C', author: 'X' });

    const all = await request(app).get('/books');
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get('/books?author=X');
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: any) => b.author === 'X')).toBe(true);
  });

  it('GET /books/:id returns 404 for missing book', async () => {
    const res = await request(app).get('/books/999');
    expect(res.status).toBe(404);
  });

  it('PUT /books/:id updates fields', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A', year: 2000 });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: 'New Title' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('A');
    expect(res.body.year).toBe(2000);
  });

  it('DELETE /books/:id removes a book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A' });
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);
    const get = await request(app).get(`/books/${created.body.id}`);
    expect(get.status).toBe(404);
  });
});
