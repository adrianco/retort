import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { BookRepository } from '../src/db.js';

let repo: BookRepository;
let app: ReturnType<typeof createApp>;

beforeEach(() => {
  repo = new BookRepository(':memory:');
  app = createApp(repo);
});

afterEach(() => {
  repo.close();
});

const sample = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' };

describe('GET /health', () => {
  it('returns ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201', async () => {
    const res = await request(app).post('/books').send(sample);
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject(sample);
    expect(res.body.id).toBe(1);
  });

  it('rejects missing title/author with 400', async () => {
    const res = await request(app).post('/books').send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.details).toHaveLength(2);
  });

  it('rejects a non-integer year', async () => {
    const res = await request(app).post('/books').send({ ...sample, year: 'nineteen' });
    expect(res.status).toBe(400);
  });

  it('rejects malformed JSON', async () => {
    const res = await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send('{not json');
    expect(res.status).toBe(400);
  });
});

describe('GET /books', () => {
  it('lists all books and filters by author', async () => {
    await request(app).post('/books').send(sample);
    await request(app).post('/books').send({ title: 'Neuromancer', author: 'William Gibson' });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(2);

    const filtered = await request(app).get('/books').query({ author: 'William Gibson' });
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].title).toBe('Neuromancer');
    expect(filtered.body[0].year).toBeNull();
  });
});

describe('GET /books/:id', () => {
  it('returns a book or 404', async () => {
    const created = await request(app).post('/books').send(sample);
    const found = await request(app).get(`/books/${created.body.id}`);
    expect(found.status).toBe(200);
    expect(found.body).toMatchObject(sample);

    const missing = await request(app).get('/books/999');
    expect(missing.status).toBe(404);

    const bad = await request(app).get('/books/abc');
    expect(bad.status).toBe(400);
  });
});

describe('PUT /books/:id', () => {
  it('updates an existing book', async () => {
    const created = await request(app).post('/books').send(sample);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ ...sample, title: 'Dune Messiah', year: 1969 });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Dune Messiah');
    expect(res.body.year).toBe(1969);
  });

  it('returns 404 for unknown id and 400 for invalid body', async () => {
    expect((await request(app).put('/books/42').send(sample)).status).toBe(404);
    const created = await request(app).post('/books').send(sample);
    expect((await request(app).put(`/books/${created.body.id}`).send({ title: '' })).status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204, then 404', async () => {
    const created = await request(app).post('/books').send(sample);
    expect((await request(app).delete(`/books/${created.body.id}`)).status).toBe(204);
    expect((await request(app).get(`/books/${created.body.id}`)).status).toBe(404);
    expect((await request(app).delete(`/books/${created.body.id}`)).status).toBe(404);
  });
});
