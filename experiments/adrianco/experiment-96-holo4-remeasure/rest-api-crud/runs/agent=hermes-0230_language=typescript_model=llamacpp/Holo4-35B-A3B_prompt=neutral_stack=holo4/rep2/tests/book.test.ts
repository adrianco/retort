import request from 'supertest';
import fs from 'fs';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'books.db');

// Delete database file before importing app (to ensure clean state)
if (fs.existsSync(DB_PATH)) {
  fs.unlinkSync(DB_PATH);
}

// Import app after deleting DB file
const app = require('../src/index').default;

describe('Books API', () => {
  describe('GET /health', () => {
    it('should return 200 with status OK', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'OK' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.status).toBe(201);
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
      expect(res.body.id).toBeDefined();
    });

    it('should return 400 if title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Test', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
    });

    it('should return 400 if author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Test', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
    });

    it('should return 409 for duplicate ISBN', async () => {
      await request(app)
        .post('/books')
        .send({ title: 'Book 1', author: 'Author 1', year: 2020, isbn: '978-1234567890' });
      const res = await request(app)
        .post('/books')
        .send({ title: 'Book 2', author: 'Author 2', year: 2021, isbn: '978-1234567890' });
      expect(res.status).toBe(409);
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      await request(app).post('/books').send({ title: 'Book A', author: 'Author X', year: 2020, isbn: '111' });
      await request(app).post('/books').send({ title: 'Book B', author: 'Author X', year: 2021, isbn: '222' });
      await request(app).post('/books').send({ title: 'Book C', author: 'Author Y', year: 2022, isbn: '333' });
    });

    it('should list all books', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body.length).toBeGreaterThanOrEqual(3);
    });

    it('should filter by author', async () => {
      const res = await request(app).get('/books?author=Author X');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body[0].author).toBe('Author X');
    });
  });

  describe('GET /books/:id', () => {
    let createdBook: any;
    beforeEach(async () => {
      const res = await request(app).post('/books').send({ title: 'Test Book', author: 'Test Author', year: 2023, isbn: '555' });
      createdBook = res.body;
    });

    it('should return a book by ID', async () => {
      const res = await request(app).get(`/books/${createdBook.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/99999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    let createdBook: any;
    beforeEach(async () => {
      const res = await request(app).post('/books').send({ title: 'Old Title', author: 'Old Author', year: 2020, isbn: '777' });
      createdBook = res.body;
    });

    it('should update a book', async () => {
      const res = await request(app)
        .put(`/books/${createdBook.id}`)
        .send({ title: 'New Title', year: 2023 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.year).toBe(2023);
      expect(res.body.author).toBe('Old Author');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).put('/books/99999').send({ title: 'New' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    let createdBook: any;
    beforeEach(async () => {
      const res = await request(app).post('/books').send({ title: 'Delete Me', author: 'Author', year: 2020, isbn: '888' });
      createdBook = res.body;
    });

    it('should delete a book', async () => {
      const res = await request(app).delete(`/books/${createdBook.id}`);
      expect(res.status).toBe(204);
      const getRes = await request(app).get(`/books/${createdBook.id}`);
      expect(getRes.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/99999');
      expect(res.status).toBe(404);
    });
  });
});
