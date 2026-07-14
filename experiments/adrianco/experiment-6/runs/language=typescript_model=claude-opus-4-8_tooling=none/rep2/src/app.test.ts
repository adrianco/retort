import request from 'supertest';
import type { Database } from 'better-sqlite3';
import { createApp } from './app';
import { createDb } from './db';

describe('Book Collection API', () => {
  let db: Database;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    db = createDb(':memory:');
    app = createApp(db);
  });

  afterEach(() => {
    db.close();
  });

  it('GET /health returns ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('POST /books creates a book and returns 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '978-0441013593' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: 'Dune',
      author: 'Frank Herbert',
      year: 1965,
      isbn: '978-0441013593',
    });
  });

  it('POST /books rejects missing title/author with 400', async () => {
    const res = await request(app).post('/books').send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toEqual(
      expect.arrayContaining([
        expect.stringContaining('title'),
        expect.stringContaining('author'),
      ])
    );
  });

  it('GET /books lists books and supports ?author= filter', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'B', author: 'Bob' });
    await request(app).post('/books').send({ title: 'C', author: 'Alice' });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get('/books').query({ author: 'Alice' });
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
  });

  it('GET /books/:id returns a book or 404', async () => {
    const created = await request(app).post('/books').send({ title: 'X', author: 'Y' });
    const id = created.body.id;

    const found = await request(app).get(`/books/${id}`);
    expect(found.status).toBe(200);
    expect(found.body.title).toBe('X');

    const missing = await request(app).get('/books/99999');
    expect(missing.status).toBe(404);
  });

  it('PUT /books/:id updates a book', async () => {
    const created = await request(app).post('/books').send({ title: 'Old', author: 'Auth' });
    const id = created.body.id;

    const updated = await request(app)
      .put(`/books/${id}`)
      .send({ title: 'New', author: 'Auth', year: 2020 });
    expect(updated.status).toBe(200);
    expect(updated.body).toMatchObject({ id, title: 'New', author: 'Auth', year: 2020 });

    const missing = await request(app)
      .put('/books/99999')
      .send({ title: 'Nope', author: 'Nobody' });
    expect(missing.status).toBe(404);
  });

  it('DELETE /books/:id removes a book and returns 204', async () => {
    const created = await request(app).post('/books').send({ title: 'Del', author: 'Me' });
    const id = created.body.id;

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);

    const after = await request(app).get(`/books/${id}`);
    expect(after.status).toBe(404);

    const delMissing = await request(app).delete('/books/99999');
    expect(delMissing.status).toBe(404);
  });
});
