import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app';
import { BookStore } from '../src/db';

describe('Book Collection API', () => {
  let app: Express;
  let store: BookStore;

  beforeEach(() => {
    store = new BookStore(':memory:');
    app = createApp(store);
  });

  afterEach(() => {
    store.close();
  });

  describe('GET /health', () => {
    it('returns 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201 with the new record', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: 'Dune',
        author: 'Frank Herbert',
        year: 1965,
        isbn: '9780441013593',
      });
    });

    it('rejects a book missing required fields with 400', async () => {
      const res = await request(app).post('/books').send({ year: 2020 });
      expect(res.status).toBe(400);
      expect(res.body.errors).toEqual(
        expect.arrayContaining([
          expect.stringMatching(/title/),
          expect.stringMatching(/author/),
        ])
      );
    });

    it('rejects whitespace-only title', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: '   ', author: 'Someone' });
      expect(res.status).toBe(400);
    });

    it('accepts a book without optional year/isbn', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Book', author: 'Author' });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe('GET /books', () => {
    it('returns an empty array initially', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it('lists all books and filters by author', async () => {
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
  });

  describe('GET /books/:id', () => {
    it('returns a single book by id', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: '1984', author: 'Orwell' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('1984');
    });

    it('returns 404 when book does not exist', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });

    it('returns 400 on invalid id', async () => {
      const res = await request(app).get('/books/abc');
      expect(res.status).toBe(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Old', author: 'Same' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'New', author: 'Same', year: 2024 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New');
      expect(res.body.year).toBe(2024);
    });

    it('returns 404 when updating non-existent book', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(404);
    });

    it('rejects update with missing fields', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'T', author: 'A' });
      const res = await request(app).put(`/books/${created.body.id}`).send({});
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes an existing book and returns 204', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Gone', author: 'Soon' });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);

      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it('returns 404 when deleting non-existent book', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
