import request from 'supertest';
import { app } from '../src/server';
import { getDb, resetDb, closeDb } from '../src/database';
import fs from 'fs';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'books.db');

// Before each test, reset the database to a clean state
beforeEach(() => {
  resetDb();
});

// After all tests, close the database
afterAll(() => {
  closeDb();
  // Clean up the database file
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }
  if (fs.existsSync(DB_PATH + '-wal')) {
    fs.unlinkSync(DB_PATH + '-wal');
  }
  if (fs.existsSync(DB_PATH + '-shm')) {
    fs.unlinkSync(DB_PATH + '-shm');
  }
});

describe('Book Collection API', () => {
  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book with all fields', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };
      const response = await request(app).post('/books').send(bookData);
      expect(response.status).toBe(201);
      expect(response.body).toMatchObject({
        title: bookData.title,
        author: bookData.author,
        year: bookData.year,
        isbn: bookData.isbn,
      });
      expect(response.body).toHaveProperty('id');
    });

    it('should create a book with minimal fields (no year, no isbn)', async () => {
      const bookData = {
        title: '1984',
        author: 'George Orwell',
      };
      const response = await request(app).post('/books').send(bookData);
      expect(response.status).toBe(201);
      expect(response.body).toMatchObject({
        title: bookData.title,
        author: bookData.author,
        year: null,
        isbn: null,
      });
    });

    it('should return 400 when title is missing', async () => {
      const response = await request(app)
        .post('/books')
        .send({ author: 'Test Author' });
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
    });

    it('should return 400 when author is missing', async () => {
      const response = await request(app)
        .post('/books')
        .send({ title: 'Test Book' });
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      // Seed some books
      await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
      await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935',
      });
      await request(app).post('/books').send({
        title: 'Animal Farm',
        author: 'George Orwell',
        year: 1945,
        isbn: '978-0451526342',
      });
    });

    it('should return all books', async () => {
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBe(3);
    });

    it('should filter books by author', async () => {
      const response = await request(app).get('/books').query({ author: 'George Orwell' });
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBe(2);
      response.body.forEach((book: any) => {
        expect(book.author).toBe('George Orwell');
      });
    });

    it('should return empty array when no books match author filter', async () => {
      const response = await request(app).get('/books').query({ author: 'Nonexistent Author' });
      expect(response.status).toBe(200);
      expect(response.body).toEqual([]);
    });
  });

  describe('GET /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'To Kill a Mockingbird',
        author: 'Harper Lee',
        year: 1960,
        isbn: '978-0061120084',
      });
      createdBook = response.body;
    });

    it('should return a book by valid ID', async () => {
      const response = await request(app).get(`/books/${createdBook.id}`);
      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        id: createdBook.id,
        title: 'To Kill a Mockingbird',
        author: 'Harper Lee',
        year: 1960,
        isbn: '978-0061120084',
      });
    });

    it('should return 404 for non-existent book ID', async () => {
      const response = await request(app).get('/books/9999');
      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('error');
    });

    it('should return 400 for invalid book ID', async () => {
      const response = await request(app).get('/books/abc');
      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('error');
    });
  });

  describe('PUT /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'Brave New World',
        author: 'Aldous Huxley',
        year: 1932,
        isbn: '978-0060850524',
      });
      createdBook = response.body;
    });

    it('should update a book with new data', async () => {
      const updateData = {
        title: 'Brave New World (Revised)',
        year: 1932,
        isbn: '978-0060850525',
      };
      const response = await request(app)
        .put(`/books/${createdBook.id}`)
        .send(updateData);
      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        id: createdBook.id,
        title: 'Brave New World (Revised)',
        author: 'Aldous Huxley',
        year: 1932,
        isbn: '978-0060850525',
      });
    });

    it('should return 404 for non-existent book ID', async () => {
      const response = await request(app)
        .put('/books/9999')
        .send({ title: 'Test', author: 'Test' });
      expect(response.status).toBe(404);
    });

    it('should return 400 when title is empty after update', async () => {
      const response = await request(app)
        .put(`/books/${createdBook.id}`)
        .send({ title: '', author: 'Test' });
      expect(response.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const response = await request(app).post('/books').send({
        title: 'The Catcher in the Rye',
        author: 'J.D. Salinger',
        year: 1951,
        isbn: '978-0316769488',
      });
      createdBook = response.body;
    });

    it('should delete a book and return 204', async () => {
      const response = await request(app).delete(`/books/${createdBook.id}`);
      expect(response.status).toBe(204);
    });

    it('should return 404 for non-existent book ID', async () => {
      const response = await request(app).delete('/books/9999');
      expect(response.status).toBe(404);
    });

    it('should not return the book after deletion', async () => {
      await request(app).delete(`/books/${createdBook.id}`);
      const response = await request(app).get(`/books/${createdBook.id}`);
      expect(response.status).toBe(404);
    });
  });
});
