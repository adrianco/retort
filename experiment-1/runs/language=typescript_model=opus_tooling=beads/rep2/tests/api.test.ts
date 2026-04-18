import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

function makeApp() {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Book API', () => {
  let app: ReturnType<typeof makeApp>;

  beforeEach(() => {
    app = makeApp();
  });

  it('GET /health returns ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('POST /books creates a book and GET /books/:id returns it', async () => {
    const create = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Herbert', year: 1965, isbn: '123' });
    expect(create.status).toBe(201);
    expect(create.body.id).toBeDefined();
    expect(create.body.title).toBe('Dune');

    const get = await request(app).get(`/books/${create.body.id}`);
    expect(get.status).toBe(200);
    expect(get.body.author).toBe('Herbert');
  });

  it('POST /books rejects missing title', async () => {
    const res = await request(app).post('/books').send({ author: 'X' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/);
  });

  it('POST /books rejects missing author', async () => {
    const res = await request(app).post('/books').send({ title: 'X' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/author/);
  });

  it('GET /books filters by author', async () => {
    await request(app)
      .post('/books')
      .send({ title: 'A', author: 'Alice' });
    await request(app)
      .post('/books')
      .send({ title: 'B', author: 'Bob' });
    await request(app)
      .post('/books')
      .send({ title: 'C', author: 'Alice' });

    const all = await request(app).get('/books');
    expect(all.body).toHaveLength(3);

    const alice = await request(app).get('/books?author=Alice');
    expect(alice.body).toHaveLength(2);
    expect(alice.body.every((b: any) => b.author === 'Alice')).toBe(true);
  });

  it('PUT /books/:id updates a book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Old', author: 'A' });
    const id = created.body.id;

    const upd = await request(app)
      .put(`/books/${id}`)
      .send({ title: 'New', author: 'A', year: 2020 });
    expect(upd.status).toBe(200);
    expect(upd.body.title).toBe('New');
    expect(upd.body.year).toBe(2020);
  });

  it('DELETE /books/:id removes a book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'X', author: 'Y' });
    const id = created.body.id;

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);

    const get = await request(app).get(`/books/${id}`);
    expect(get.status).toBe(404);
  });

  it('GET /books/:id returns 404 for missing', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
  });
});
