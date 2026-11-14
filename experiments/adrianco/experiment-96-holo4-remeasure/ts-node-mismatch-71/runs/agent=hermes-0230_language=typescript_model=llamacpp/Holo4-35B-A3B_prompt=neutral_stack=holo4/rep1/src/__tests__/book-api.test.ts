import request from 'supertest';
import app from '../index';
import { clearAllBooks, initializeDatabase } from '../database';

beforeEach(() => {
  process.env.NODE_ENV = 'test';
  initializeDatabase();
  clearAllBooks();
});

describe('Book API', () => {
  describe('GET /health', () => {
    it('should return 200 with status OK', async () => {
      const res = await request(app).get('/api/health');
      expect(res.statusCode).toBe(200);
      expect(res.body).toEqual({ status: 'OK' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
    });

    it('should return 400 if title is missing', async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(400);
      expect(res.body.errors).toContain('title is required');
    });

    it('should return 400 if author is missing', async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', year: 1925, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(400);
      expect(res.body.errors).toContain('author is required');
    });

    it('should return 409 if ISBN already exists', async () => {
      await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'Another Book', author: 'Someone', year: 2020, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(409);
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      await request(app)
        .post('/api/books')
        .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });
    });

    it('should list all books', async () => {
      const res = await request(app).get('/api/books');
      expect(res.statusCode).toBe(200);
      expect(res.body).toHaveLength(2);
    });

    it('should filter by author', async () => {
      const res = await request(app).get('/api/books').query({ author: 'F. Scott Fitzgerald' });
      expect(res.statusCode).toBe(200);
      expect(res.body).toHaveLength(1);
      expect(res.body[0].author).toBe('F. Scott Fitzgerald');
    });
  });

  describe('GET /books/:id', () => {
    let bookId: number;
    beforeEach(async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      bookId = res.body.id;
    });

    it('should get a single book', async () => {
      const res = await request(app).get(`/api/books/${bookId}`);
      expect(res.statusCode).toBe(200);
      expect(res.body.title).toBe('The Great Gatsby');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/api/books/9999');
      expect(res.statusCode).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    let bookId: number;
    beforeEach(async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      bookId = res.body.id;
    });

    it('should update a book', async () => {
      const res = await request(app)
        .put(`/api/books/${bookId}`)
        .send({ title: 'The Great Gatsby (Updated)' });
      expect(res.statusCode).toBe(200);
      expect(res.body.title).toBe('The Great Gatsby (Updated)');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/api/books/9999')
        .send({ title: 'New Title' });
      expect(res.statusCode).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    let bookId: number;
    beforeEach(async () => {
      const res = await request(app)
        .post('/api/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      bookId = res.body.id;
    });

    it('should delete a book', async () => {
      const res = await request(app).delete(`/api/books/${bookId}`);
      expect(res.statusCode).toBe(204);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/api/books/9999');
      expect(res.statusCode).toBe(404);
    });
  });
});
