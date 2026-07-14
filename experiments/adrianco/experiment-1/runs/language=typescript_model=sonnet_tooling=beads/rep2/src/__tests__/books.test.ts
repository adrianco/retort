import request from 'supertest';
import { createApp } from '../app';
import { createTestDb } from '../database';
import Database from 'better-sqlite3';

describe('Books API', () => {
  let db: Database.Database;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    db = createTestDb();
    app = createApp(db);
  });

  afterEach(() => {
    db.close();
  });

  // --- Health check ---
  describe('GET /health', () => {
    it('returns 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  // --- POST /books ---
  describe('POST /books', () => {
    it('creates a book with valid data', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Clean Code', author: 'Robert Martin', year: 2008, isbn: '9780132350884' });

      expect(res.status).toBe(201);
      expect(res.body.id).toBeDefined();
      expect(res.body.title).toBe('Clean Code');
      expect(res.body.author).toBe('Robert Martin');
      expect(res.body.year).toBe(2008);
      expect(res.body.isbn).toBe('9780132350884');
    });

    it('creates a book with only required fields', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Minimal Book', author: 'Some Author' });

      expect(res.status).toBe(201);
      expect(res.body.title).toBe('Minimal Book');
      expect(res.body.author).toBe('Some Author');
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });

    it('returns 400 when title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Some Author' });

      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/i);
    });

    it('returns 400 when author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Some Title' });

      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/i);
    });

    it('returns 400 when title is empty string', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: '   ', author: 'Author' });

      expect(res.status).toBe(400);
    });
  });

  // --- GET /books ---
  describe('GET /books', () => {
    beforeEach(async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });
      await request(app).post('/books').send({ title: 'Book C', author: 'Alice' });
    });

    it('returns all books', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it('filters books by author', async () => {
      const res = await request(app).get('/books?author=Alice');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === 'Alice')).toBe(true);
    });

    it('returns empty array when no books match filter', async () => {
      const res = await request(app).get('/books?author=Nobody');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(0);
    });
  });

  // --- GET /books/:id ---
  describe('GET /books/:id', () => {
    it('returns a specific book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Target Book', author: 'Author' });

      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Target Book');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request(app).get('/books/99999');
      expect(res.status).toBe(404);
    });

    it('returns 400 for invalid id', async () => {
      const res = await request(app).get('/books/not-a-number');
      expect(res.status).toBe(400);
    });
  });

  // --- PUT /books/:id ---
  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Old Title', author: 'Old Author', year: 2000 });

      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'New Title', author: 'New Author', year: 2024 });

      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.author).toBe('New Author');
      expect(res.body.year).toBe(2024);
    });

    it('returns 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/books/99999')
        .send({ title: 'Title', author: 'Author' });

      expect(res.status).toBe(404);
    });

    it('returns 400 if title is cleared', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Title', author: 'Author' });

      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: '', author: 'Author' });

      expect(res.status).toBe(400);
    });
  });

  // --- DELETE /books/:id ---
  describe('DELETE /books/:id', () => {
    it('deletes a book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'To Delete', author: 'Author' });

      const delRes = await request(app).delete(`/books/${created.body.id}`);
      expect(delRes.status).toBe(204);

      const getRes = await request(app).get(`/books/${created.body.id}`);
      expect(getRes.status).toBe(404);
    });

    it('returns 404 when deleting non-existent book', async () => {
      const res = await request(app).delete('/books/99999');
      expect(res.status).toBe(404);
    });
  });
});
