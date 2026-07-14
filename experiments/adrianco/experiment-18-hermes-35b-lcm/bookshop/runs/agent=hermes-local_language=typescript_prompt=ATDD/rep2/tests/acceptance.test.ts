/**
 * Acceptance Tests — Book API REST Service
 *
 * Tests exercise the system exclusively through its public HTTP interface.
 * Each scenario starts from a clean/empty state (fresh DB).
 * All tests are atomic and independent.
 *
 * Perspective: external client of the service.
 * Language: problem domain (create a book, list books, filter by author, etc.)
 */

import request from 'supertest';
import { createApp } from '../src/app';
import { createDb, clearAll } from '../src/db';

describe('Book API — Acceptance Tests', () => {
  let app: any;

  beforeEach(() => {
    // Fresh DB per test — system starts empty
    const db = createDb(':memory:');
    app = createApp(db);
  });

  // ─── Health Check ────────────────────────────────────────────────────────

  describe('GET /health', () => {
    it('returns 200 with status "ok"', async () => {
      const res = await request(app).get('/health').send();
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  // ─── Create a Book ───────────────────────────────────────────────────────

  describe('POST /books — create a new book', () => {
    it('creates a book when all required fields are provided', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0743273565',
        });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
    });

    it('rejects a book with a missing title', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          author: 'George Orwell',
          year: 1949,
          isbn: '978-0451524935',
        });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('title is required');
    });

    it('rejects a book with a missing author', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          title: '1984',
          year: 1949,
          isbn: '978-0451524935',
        });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('author is required');
    });

    it('returns unique IDs for each book', async () => {
      const res1 = await request(app)
        .post('/books')
        .send({ title: 'Book A', author: 'Author A' });
      const res2 = await request(app)
        .post('/books')
        .send({ title: 'Book B', author: 'Author B' });
      expect(res1.status).toBe(201);
      expect(res2.status).toBe(201);
      expect(res1.body.id).not.toEqual(res2.body.id);
    });
  });

  // ─── List All Books ──────────────────────────────────────────────────────

  describe('GET /books — list all books', () => {
    it('returns an empty list when no books exist', async () => {
      const res = await request(app).get('/books').send();
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ books: [] });
    });

    it('returns all books when books exist', async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author A', year: 2000, isbn: '111' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Author B', year: 2010, isbn: '222' });
      await request(app).post('/books').send({ title: 'Book C', author: 'Author A', year: 2020, isbn: '333' });

      const res = await request(app).get('/books').send();
      expect(res.status).toBe(200);
      expect(res.body.books.length).toBe(3);
    });

    it('returns books filtered by author when ?author= is provided', async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author A', year: 2000, isbn: '111' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Author B', year: 2010, isbn: '222' });
      await request(app).post('/books').send({ title: 'Book C', author: 'Author A', year: 2020, isbn: '333' });

      const res = await request(app)
        .get('/books?author=Author%20A')
        .send();
      expect(res.status).toBe(200);
      expect(res.body.books.length).toBe(2);
      expect(res.body.books[0].author).toBe('Author A');
      expect(res.body.books[1].author).toBe('Author A');
    });

    it('returns empty list when ?author= matches no one', async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author A', year: 2000, isbn: '111' });

      const res = await request(app)
        .get('/books?author=Nobody')
        .send();
      expect(res.status).toBe(200);
      expect(res.body.books).toEqual([]);
    });
  });

  // ─── Get a Single Book ───────────────────────────────────────────────────

  describe('GET /books/:id — get a single book', () => {
    it('returns the book when the ID exists', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '978-0441172719' });
      const bookId = createRes.body.id;

      const res = await request(app).get(`/books/${bookId}`).send();
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({
        id: bookId,
        title: 'Dune',
        author: 'Frank Herbert',
        year: 1965,
        isbn: '978-0441172719',
      });
    });

    it('returns 404 when the ID does not exist', async () => {
      const res = await request(app).get('/books/9999').send();
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });

  // ─── Update a Book ───────────────────────────────────────────────────────

  describe('PUT /books/:id — update a book', () => {
    it('updates the book and returns the updated version', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Old Title', author: 'Old Author', year: 2000, isbn: '111' });
      const bookId = createRes.body.id;

      const res = await request(app)
        .put(`/books/${bookId}`)
        .send({ title: 'New Title', author: 'New Author', year: 2024, isbn: '999' });
      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({
        id: bookId,
        title: 'New Title',
        author: 'New Author',
        year: 2024,
        isbn: '999',
      });
    });

    it('returns 404 when the ID does not exist', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'Ghost', author: 'Nobody' });
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });

    it('rejects update with missing title', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Old Title', author: 'Author', year: 2000, isbn: '111' });
      const bookId = createRes.body.id;

      const res = await request(app)
        .put(`/books/${bookId}`)
        .send({ author: 'Updated Author', year: 2024 });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('title is required');
    });

    it('rejects update with missing author', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'Title', author: 'Old Author', year: 2000, isbn: '111' });
      const bookId = createRes.body.id;

      const res = await request(app)
        .put(`/books/${bookId}`)
        .send({ title: 'Updated Title', year: 2024 });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('author is required');
    });
  });

  // ─── Delete a Book ───────────────────────────────────────────────────────

  describe('DELETE /books/:id — delete a book', () => {
    it('deletes the book and returns 200', async () => {
      const createRes = await request(app)
        .post('/books')
        .send({ title: 'To Delete', author: 'Author', year: 2000, isbn: '111' });
      const bookId = createRes.body.id;

      const res = await request(app).delete(`/books/${bookId}`).send();
      expect(res.status).toBe(200);
      expect(res.body.message).toBe('Book deleted');

      // Verify the book is gone
      const verifyRes = await request(app).get('/books').send();
      expect(verifyRes.body.books.length).toBe(0);
    });

    it('returns 404 when the ID does not exist', async () => {
      const res = await request(app).delete('/books/9999').send();
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });
});
