import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

function makeApp() {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Books API', () => {
  describe('GET /health', () => {
    it('returns 200 ok', async () => {
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
        title: 'Dune',
        author: 'Frank Herbert',
        year: 1965,
        isbn: '978-0441172719',
      });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: 1,
        title: 'Dune',
        author: 'Frank Herbert',
        year: 1965,
        isbn: '978-0441172719',
      });
    });

    it('rejects missing title with 400', async () => {
      const app = makeApp();
      const res = await request(app).post('/books').send({ author: 'X' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/);
    });

    it('rejects missing author with 400', async () => {
      const app = makeApp();
      const res = await request(app).post('/books').send({ title: 'X' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/);
    });
  });

  describe('GET /books', () => {
    it('returns empty array when no books exist', async () => {
      const app = makeApp();
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it('lists books and filters by author', async () => {
      const app = makeApp();
      await request(app).post('/books').send({ title: 'A', author: 'Alice' });
      await request(app).post('/books').send({ title: 'B', author: 'Bob' });
      await request(app).post('/books').send({ title: 'C', author: 'Alice' });

      const all = await request(app).get('/books');
      expect(all.status).toBe(200);
      expect(all.body).toHaveLength(3);

      const alice = await request(app).get('/books?author=Alice');
      expect(alice.status).toBe(200);
      expect(alice.body).toHaveLength(2);
      expect(alice.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('returns the book when it exists', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'A', author: 'Alice' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({ title: 'A', author: 'Alice' });
    });

    it('returns 404 when not found', async () => {
      const app = makeApp();
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'Old', author: 'Alice', year: 2000 });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'New', author: 'Alice', year: 2024 });
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({
        id: created.body.id,
        title: 'New',
        author: 'Alice',
        year: 2024,
      });
    });

    it('returns 404 when updating a missing book', async () => {
      const app = makeApp();
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(404);
    });

    it('rejects empty title with 400', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'A', author: 'Alice' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: '   ' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book and returns 204', async () => {
      const app = makeApp();
      const created = await request(app)
        .post('/books')
        .send({ title: 'A', author: 'Alice' });
      const res = await request(app).delete(`/books/${created.body.id}`);
      expect(res.status).toBe(204);

      const after = await request(app).get(`/books/${created.body.id}`);
      expect(after.status).toBe(404);
    });

    it('returns 404 when deleting a missing book', async () => {
      const app = makeApp();
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
