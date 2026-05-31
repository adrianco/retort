import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app';

let app: Express;

beforeEach(() => {
  ({ app } = createApp());
});

describe('GET /health', () => {
  it('returns 200 and status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201 with id', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'The Hobbit', author: 'J.R.R. Tolkien', year: 1937, isbn: '978-0547928227' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0547928227',
    });
    expect(typeof res.body.id).toBe('number');
  });

  it('rejects missing title with 400', async () => {
    const res = await request(app).post('/books').send({ author: 'Anon' });
    expect(res.status).toBe(400);
    expect(res.body.errors).toEqual(
      expect.arrayContaining([expect.stringMatching(/title is required/)])
    );
  });

  it('rejects missing author with 400', async () => {
    const res = await request(app).post('/books').send({ title: 'Untitled' });
    expect(res.status).toBe(400);
    expect(res.body.errors).toEqual(
      expect.arrayContaining([expect.stringMatching(/author is required/)])
    );
  });

  it('rejects non-integer year with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'X', author: 'Y', year: 'not-a-year' });
    expect(res.status).toBe(400);
  });
});

describe('GET /books', () => {
  it('returns all books, optionally filtered by author', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'B', author: 'Bob' });
    await request(app).post('/books').send({ title: 'C', author: 'Alice' });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get('/books?author=Alice');
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
  });
});

describe('GET /books/:id', () => {
  it('returns a single book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Solo', author: 'Author' });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Solo');
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).get('/books/999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  it('updates an existing book', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Old', author: 'Author' });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: 'New', author: 'Author', year: 2020 });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New');
    expect(res.body.year).toBe(2020);
  });

  it('returns 404 when updating unknown id', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'X', author: 'Y' });
    expect(res.status).toBe(404);
  });

  it('returns 400 when update body is invalid', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Keep', author: 'Author' });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: '' });
    expect(res.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book and then returns 404 on re-fetch', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Disposable', author: 'Author' });
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const fetched = await request(app).get(`/books/${created.body.id}`);
    expect(fetched.status).toBe(404);
  });

  it('returns 404 when deleting an unknown id', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
