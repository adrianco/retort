import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

function makeApp(): Express {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Books API', () => {
  describe('GET /health', () => {
    it('returns 200 with ok status', async () => {
      const app = makeApp();
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201', async () => {
      const app = makeApp();
      const res = await request(app).post('/books').send({
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        year: 1937,
        isbn: '978-0345339683',
      });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        year: 1937,
        isbn: '978-0345339683',
      });
    });

    it('returns 400 when title is missing', async () => {
      const app = makeApp();
      const res = await request(app).post('/books').send({ author: 'Someone' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/);
    });

    it('returns 400 when author is missing', async () => {
      const app = makeApp();
      const res = await request(app).post('/books').send({ title: 'Untitled' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/);
    });

    it('returns 400 when year is not an integer', async () => {
      const app = makeApp();
      const res = await request(app)
        .post('/books')
        .send({ title: 'X', author: 'Y', year: 'not-a-number' });
      expect(res.status).toBe(400);
    });
  });

  describe('GET /books', () => {
    it('returns an empty list initially', async () => {
      const app = makeApp();
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it('lists all books', async () => {
      const app = makeApp();
      await request(app).post('/books').send({ title: 'A', author: 'X' });
      await request(app).post('/books').send({ title: 'B', author: 'Y' });
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it('filters by author', async () => {
      const app = makeApp();
      await request(app).post('/books').send({ title: 'A', author: 'Alice' });
      await request(app).post('/books').send({ title: 'B', author: 'Bob' });
      await request(app).post('/books').send({ title: 'C', author: 'Alice' });
      const res = await request(app).get('/books?author=Alice');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('returns the book when it exists', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Dune');
    });

    it('returns 404 when the book does not exist', async () => {
      const app = makeApp();
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'Old', author: 'A' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'New', author: 'A', year: 2020 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New');
      expect(res.body.year).toBe(2020);
    });

    it('returns 404 for missing book', async () => {
      const app = makeApp();
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(404);
    });

    it('returns 400 for invalid input on update', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'T', author: 'A' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ author: 'A' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes an existing book', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'Gone', author: 'A' });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);
      const lookup = await request(app).get(`/books/${created.body.id}`);
      expect(lookup.status).toBe(404);
    });

    it('returns 404 for missing book', async () => {
      const app = makeApp();
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
