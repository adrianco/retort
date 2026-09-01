import request from 'supertest';
import app from '../src/app';
import * as db from '../src/database';

describe('Book Collection API', () => {
  beforeEach(() => {
    db.resetDb();
  });

  afterAll(() => {
    db.closeDb();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.statusCode).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a book with all fields', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
    });

    it('should create a book with minimal fields (title and author only)', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: '1984', author: 'George Orwell' });
      expect(res.statusCode).toBe(201);
      expect(res.body.title).toBe('1984');
      expect(res.body.author).toBe('George Orwell');
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });

    it('should return 400 when title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Some Author' });
      expect(res.statusCode).toBe(400);
      expect(res.body.error).toBe('title and author are required');
    });

    it('should return 400 when author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Some Title' });
      expect(res.statusCode).toBe(400);
      expect(res.body.error).toBe('title and author are required');
    });
  });

  describe('GET /books', () => {
    it('should list all books', async () => {
      // First create a book
      await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      const res = await request(app).get('/books');
      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBeGreaterThan(0);
    });

    it('should filter books by author', async () => {
      // Create two books by different authors
      await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925 });
      await request(app)
        .post('/books')
        .send({ title: '1984', author: 'George Orwell', year: 1949 });

      const res = await request(app).get('/books').query({ author: 'F. Scott Fitzgerald' });
      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(1);
      expect(res.body[0].author).toBe('F. Scott Fitzgerald');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      const res = await request(app).get('/books/1');
      expect(res.statusCode).toBe(200);
      expect(res.body.id).toBe(1);
      expect(res.body.title).toBe('The Great Gatsby');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.statusCode).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const res = await request(app).get('/books/abc');
      expect(res.statusCode).toBe(400);
      expect(res.body.error).toBe('Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      const res = await request(app)
        .put('/books/1')
        .send({ title: 'The Great Gatsby (Updated)' });
      expect(res.statusCode).toBe(200);
      expect(res.body.title).toBe('The Great Gatsby (Updated)');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'Nonexistent' });
      expect(res.statusCode).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      const res = await request(app).delete('/books/1');
      expect(res.statusCode).toBe(204);

      // Verify it's gone
      const getRes = await request(app).get('/books/1');
      expect(getRes.statusCode).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.statusCode).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });
});
