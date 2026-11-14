const request = require('supertest');
const fs = require('fs');
const path = require('path');

let app;

beforeAll(async () => {
  const dbPath = path.join(__dirname, '..', 'books.db');
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }
  const appModule = require('../dist/app');
  app = appModule.app;
});

describe('Book API', () => {
  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.statusCode).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a book', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.statusCode).toBe(201);
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
      expect(res.body.id).toBeDefined();
    });

    it('should return 400 if title or author is missing', async () => {
      const res = await request(app).post('/books').send({ author: 'No Title' });
      expect(res.statusCode).toBe(400);
      expect(res.body.error).toBe('Title and author are required');
    });
  });

  describe('GET /books', () => {
    it('should list all books', async () => {
      const res = await request(app).get('/books');
      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
    });

    it('should filter books by author', async () => {
      const res = await request(app).get('/books').query({ author: 'F. Scott Fitzgerald' });
      expect(res.statusCode).toBe(200);
      expect(res.body.every(b => b.author === 'F. Scott Fitzgerald')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('should get a book by id', async () => {
      const res = await request(app).get('/books/1');
      expect(res.statusCode).toBe(200);
      expect(res.body.title).toBe('The Great Gatsby');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.statusCode).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      const res = await request(app)
        .put('/books/1')
        .send({ year: 1926 });
      expect(res.statusCode).toBe(200);
      expect(res.body.year).toBe(1926);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).put('/books/9999').send({ title: 'X' });
      expect(res.statusCode).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      const res = await request(app).delete('/books/1');
      expect(res.statusCode).toBe(204);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.statusCode).toBe(404);
    });
  });
});
