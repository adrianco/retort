import request from 'supertest';
import app from '../server';
import sqlite3 from 'sqlite3';

const api = request(app);

// Create a simple database setup function
async function setupTestDB(): Promise<sqlite3.Database> {
  const testDb = './test-books.db';
  const db = new sqlite3.Database(testDb);
  
  // Create table
  await new Promise<void>((resolve, reject) => {
    db.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        isbn TEXT NOT NULL
      )
    `, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
  
  return db;
}

// Simple clean function
async function cleanBooks(db: sqlite3.Database, titlePattern: string) {
  await new Promise<void>((resolve, reject) => {
    db.run(`DELETE FROM books WHERE title ${titlePattern}`, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

describe('Book API', () => {
  const testBook = {
    title: 'The Testing Book',
    author: 'Test Author',
    year: 2024,
    isbn: '978-1234567890'
  };

  let bookId: number;
  let db: sqlite3.Database;

  beforeAll(async () => {
    db = await setupTestDB();
  });

  beforeEach(async () => {
    await cleanBooks(db, "= 'The Testing Book'");
    await cleanBooks(db, "LIKE 'Book %'");
  });

  afterAll(async () => {
    if (db) {
      await new Promise<void>((resolve, reject) => {
        db.close((err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    }
    // Clean up test database file
    const fs = require('fs');
    if (fs.existsSync('./test-books.db')) {
      fs.unlinkSync('./test-books.db');
    }
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const res = await api.post('/books').send(testBook);
      expect(res.status).toBe(201);
      expect(res.body.title).toBe(testBook.title);
      expect(res.body.author).toBe(testBook.author);
      expect(res.body.year).toBe(testBook.year);
      expect(res.body.isbn).toBe(testBook.isbn);
      expect(res.body.id).toBeDefined();
      bookId = res.body.id;
    });

    it('should return 400 if title is missing', async () => {
      const res = await api.post('/books').send({
        author: testBook.author,
        year: testBook.year,
        isbn: testBook.isbn
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Title is required');
    });

    it('should return 400 if author is missing', async () => {
      const res = await api.post('/books').send({
        title: testBook.title,
        year: testBook.year,
        isbn: testBook.isbn
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Author is required');
    });

    it('should return 400 if year is missing', async () => {
      const res = await api.post('/books').send({
        title: testBook.title,
        author: testBook.author,
        isbn: testBook.isbn
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Year is required');
    });

    it('should return 400 if isbn is missing', async () => {
      const res = await api.post('/books').send({
        title: testBook.title,
        author: testBook.author,
        year: testBook.year
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('ISBN is required');
    });
  });

  describe('GET /books', () => {
    it('should return all books', async () => {
      // Create a test book first
      await api.post('/books').send(testBook);

      const res = await api.get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBeGreaterThan(0);
    });

    it('should filter books by author', async () => {
      // Create books with different authors
      await api.post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '978-1111111111'
      });
      await api.post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '978-2222222222'
      });

      const res = await api.get('/books?author=Author%20A');
      expect(res.status).toBe(200);
      expect(res.body.length).toBe(1);
      expect(res.body[0].author).toBe('Author A');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a single book by ID', async () => {
      const createRes = await api.post('/books').send(testBook);
      bookId = createRes.body.id;

      const res = await api.get(`/books/${bookId}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe(testBook.title);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await api.get('/books/99999');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });

    it('should return 400 for invalid ID format', async () => {
      const res = await api.get('/books/invalid');
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      const createRes = await api.post('/books').send(testBook);
      bookId = createRes.body.id;

      const updateData = {
        title: 'Updated Title',
        author: 'Updated Author'
      };

      const res = await api.put(`/books/${bookId}`).send(updateData);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Updated Title');
      expect(res.body.author).toBe('Updated Author');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await api.put('/books/99999').send({ title: 'Updated' });
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });

    it('should return 400 for invalid ID format', async () => {
      const res = await api.put('/books/invalid').send({ title: 'Updated' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Invalid book ID');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      const createRes = await api.post('/books').send(testBook);
      bookId = createRes.body.id;

      const res = await api.delete(`/books/${bookId}`);
      expect(res.status).toBe(204);

      // Verify the book is deleted
      const getRes = await api.get(`/books/${bookId}`);
      expect(getRes.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await api.delete('/books/99999');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });
});
