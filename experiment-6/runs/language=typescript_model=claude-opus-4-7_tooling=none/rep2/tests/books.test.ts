import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

describe('Book Collection API', () => {
  let app: Express;

  beforeEach(() => {
    const db = createDb(':memory:');
    app = createApp(db);
  });

  describe('GET /health', () => {
    it('returns 200 and a status payload', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201 with the new record', async () => {
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

    it('rejects a book missing title with 400', async () => {
      const res = await request(app).post('/books').send({ author: 'Anonymous' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/);
    });

    it('rejects a book missing author with 400', async () => {
      const res = await request(app).post('/books').send({ title: 'Untitled' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/);
    });

    it('rejects a book with empty title with 400', async () => {
      const res = await request(app).post('/books').send({ title: '   ', author: 'Someone' });
      expect(res.status).toBe(400);
    });

    it('rejects a non-integer year with 400', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'X', author: 'Y', year: 'nineteen' });
      expect(res.status).toBe(400);
    });

    it('allows omitting optional year and isbn', async () => {
      const res = await request(app).post('/books').send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      await request(app).post('/books').send({ title: 'B', author: 'Beta' });
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it('filters by author query parameter', async () => {
      await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      await request(app).post('/books').send({ title: 'B', author: 'Beta' });
      await request(app).post('/books').send({ title: 'C', author: 'Alpha' });

      const res = await request(app).get('/books?author=Alpha');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === 'Alpha')).toBe(true);
    });

    it('returns an empty array when no books match the filter', async () => {
      await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      const res = await request(app).get('/books?author=Nobody');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });
  });

  describe('GET /books/:id', () => {
    it('returns the requested book', async () => {
      const created = await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(created.body.id);
    });

    it('returns 404 for an unknown id', async () => {
      const res = await request(app).get('/books/999');
      expect(res.status).toBe(404);
    });

    it('returns 400 for an invalid id', async () => {
      const res = await request(app).get('/books/not-a-number');
      expect(res.status).toBe(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const created = await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'A2', author: 'Alpha', year: 2020 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('A2');
      expect(res.body.year).toBe(2020);
    });

    it('returns 404 when updating a missing book', async () => {
      const res = await request(app).put('/books/999').send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(404);
    });

    it('returns 400 when body is invalid', async () => {
      const created = await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      const res = await request(app).put(`/books/${created.body.id}`).send({ title: 'A' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes an existing book and returns 204', async () => {
      const created = await request(app).post('/books').send({ title: 'A', author: 'Alpha' });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);

      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it('returns 404 when deleting a missing book', async () => {
      const res = await request(app).delete('/books/999');
      expect(res.status).toBe(404);
    });
  });
});
