import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { BookRepository } from '../src/db.js';

let repo: BookRepository;
let app: ReturnType<typeof createApp>;

beforeEach(() => {
  repo = new BookRepository(':memory:');
  app = createApp(repo);
});
afterEach(() => repo.close());

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

  it('rejects missing title and author with 400', async () => {
    const res = await request(app).post('/books').send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toHaveLength(2);
  });

  it('rejects invalid year', async () => {
    const res = await request(app).post('/books').send({ ...sample, year: 'abc' });
    expect(res.status).toBe(400);
  });

  it('rejects malformed JSON', async () => {
    const res = await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send('{bad json');
    expect(res.status).toBe(400);
  });
});

describe('GET /books', () => {
  it('lists all books and filters by author', async () => {
    await request(app).post('/books').send(sample);
    await request(app).post('/books').send({ title: 'Emma', author: 'Jane Austen' });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(2);

    const filtered = await request(app).get('/books').query({ author: 'Jane Austen' });
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].title).toBe('Emma');
    expect(filtered.body[0].year).toBeNull();
  });
});

describe('GET /books/:id', () => {
  it('returns a book or 404', async () => {
    await request(app).post('/books').send(sample);
    expect((await request(app).get('/books/1')).status).toBe(200);
    expect((await request(app).get('/books/99')).status).toBe(404);
    expect((await request(app).get('/books/abc')).status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates a book', async () => {
    await request(app).post('/books').send(sample);
    const res = await request(app).put('/books/1').send({ ...sample, title: 'Dune Messiah' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Dune Messiah');
    expect((await request(app).get('/books/1')).body.title).toBe('Dune Messiah');
  });

  it('returns 404 for unknown id and 400 for invalid body', async () => {
    expect((await request(app).put('/books/42').send(sample)).status).toBe(404);
    await request(app).post('/books').send(sample);
    expect((await request(app).put('/books/1').send({ title: '' })).status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and returns 204, then 404', async () => {
    await request(app).post('/books').send(sample);
    expect((await request(app).delete('/books/1')).status).toBe(204);
    expect((await request(app).get('/books/1')).status).toBe(404);
    expect((await request(app).delete('/books/1')).status).toBe(404);
  });
});
