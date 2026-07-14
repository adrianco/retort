import request from 'supertest';
import { Express } from 'express';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

describe('Book Collection API', () => {
  let app: Express;

  beforeEach(() => {
    // Fresh in-memory DB per test for isolation
    app = createApp(createDb(':memory:'));
  });

  describe('GET /health', () => {
    it('returns ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book with valid input', async () => {
      const res = await request(app).post('/books').send({
        title: 'The Go Programming Language',
        author: 'Donovan & Kernighan',
        year: 2015,
        isbn: '978-0134190440',
      });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: 'The Go Programming Language',
        author: 'Donovan & Kernighan',
        year: 2015,
        isbn: '978-0134190440',
      });
    });

    it('rejects missing title and author with 400', async () => {
      const res = await request(app).post('/books').send({ year: 2020 });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining([
          expect.stringContaining('title'),
          expect.stringContaining('author'),
        ])
      );
    });

    it('rejects a non-integer year with 400', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'X', author: 'Y', year: 'soon' });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining([expect.stringContaining('year')])
      );
    });
  });

  describe('GET /books', () => {
    it('lists books and supports the ?author= filter', async () => {
      await request(app).post('/books').send({ title: 'A', author: 'Alice' });
      await request(app).post('/books').send({ title: 'B', author: 'Bob' });
      await request(app).post('/books').send({ title: 'C', author: 'Alice' });

      const all = await request(app).get('/books');
      expect(all.status).toBe(200);
      expect(all.body).toHaveLength(3);

      const byAlice = await request(app).get('/books?author=Alice');
      expect(byAlice.status).toBe(200);
      expect(byAlice.body).toHaveLength(2);
      expect(byAlice.body.every((b: any) => b.author === 'Alice')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('returns a single book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Solo', author: 'Han' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Solo');
    });

    it('returns 404 for an unknown id', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Old', author: 'Auth' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'New', author: 'Auth', year: 2001 });
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({ title: 'New', year: 2001 });
    });

    it('returns 404 when updating a missing book', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'Nope', author: 'None' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes an existing book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Doomed', author: 'X' });
      const del = await request(app).delete(`/books/${created.body.id}`);
      expect(del.status).toBe(204);

      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it('returns 404 when deleting a missing book', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
