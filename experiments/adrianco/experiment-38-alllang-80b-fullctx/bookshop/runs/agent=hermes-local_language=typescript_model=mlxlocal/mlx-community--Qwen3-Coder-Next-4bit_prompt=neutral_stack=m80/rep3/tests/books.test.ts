import * as sqlite3 from 'sqlite3';
import { describe, it, beforeAll, afterAll, beforeEach, afterEach } from '@jest/globals';
import request = require('supertest');
import app from '../src/server';

// Use a different port for tests to avoid conflicts
const testPort = 3002;

// Create a test server that we can close after tests
let testServer: any = null;

// Use in-memory database for tests
let testDb: sqlite3.Database | null = null;

beforeAll((done) => {
  // Set up test database
  testDb = new sqlite3.Database(':memory:');
  testDb.serialize(() => {
    testDb!.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  });
  
  // Set the test database for the server
  const { setTestDatabase } = require('../src/database');
  setTestDatabase(testDb);
  
  testServer = app.listen(testPort, done);
});

afterAll(async () => {
  if (testServer) {
    await new Promise((resolve) => {
      testServer.close(resolve);
    });
  }
  if (testDb) {
    testDb.close(() => {});
  }
});

describe('Book API', () => {
  beforeEach(async () => {
    // Clear the database before each test
    if (testDb) {
      await new Promise<void>((resolve) => {
        testDb!.run('DELETE FROM books', resolve);
      });
    }
  });

  describe('GET /api/health', () => {
    it('should return health status', async () => {
      const res = await request(`http://localhost:${testPort}`).get('/api/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('ok');
      expect(res.body.timestamp).toBeDefined();
    });
  });

  describe('GET /api/books', () => {
    it('should return all books', async () => {
      // First create a book
      await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2024, isbn: '1234567890' });

      const res = await request(`http://localhost:${testPort}`).get('/api/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBeGreaterThan(0);
      expect(res.body[0].title).toBe('Test Book');
    });

    it('should filter by author', async () => {
      // Create a book with specific author
      await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2024, isbn: '1234567890' });

      const res = await request(`http://localhost:${testPort}`).get('/api/books?author=Test%20Author');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(1);
      expect(res.body[0].author).toBe('Test Author');
    });
  });

  describe('POST /api/books', () => {
    it('should create a new book', async () => {
      const res = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'New Book', author: 'New Author', year: 2024, isbn: '1111111111' });
      expect(res.status).toBe(201);
      expect(res.body.title).toBe('New Book');
      expect(res.body.author).toBe('New Author');
      expect(res.body.year).toBe(2024);
      expect(res.body.isbn).toBe('1111111111');
      expect(res.body.id).toBeDefined();
    });

    it('should return 400 if title is missing', async () => {
      const res = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ author: 'Some Author' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Title is required');
    });

    it('should return 400 if author is missing', async () => {
      const res = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Some Title' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Author is required');
    });
  });

  describe('GET /api/books/:id', () => {
    it('should return a single book by ID', async () => {
      // Create a book first
      const createRes = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Get Book', author: 'Get Author', year: 2024, isbn: '2222222222' });
      const bookId = createRes.body.id;

      const res = await request(`http://localhost:${testPort}`).get(`/api/books/${bookId}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Get Book');
      expect(res.body.author).toBe('Get Author');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(`http://localhost:${testPort}`).get('/api/books/99999');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });

  describe('PUT /api/books/:id', () => {
    it('should update a book', async () => {
      // Create a book first
      const createRes = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Update Book', author: 'Update Author', year: 2024, isbn: '3333333333' });
      const bookId = createRes.body.id;

      const res = await request(`http://localhost:${testPort}`)
        .put(`/api/books/${bookId}`)
        .send({ title: 'Updated Book', author: 'Updated Author', year: 2025, isbn: '4444444444' });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Updated Book');
      expect(res.body.author).toBe('Updated Author');
      expect(res.body.year).toBe(2025);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(`http://localhost:${testPort}`)
        .put('/api/books/99999')
        .send({ title: 'Non-existent', author: 'Non-existent', year: 2024, isbn: '5555555555' });
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });

  describe('DELETE /api/books/:id', () => {
    it('should delete a book', async () => {
      // Create a book first
      const createRes = await request(`http://localhost:${testPort}`)
        .post('/api/books')
        .send({ title: 'Delete Book', author: 'Delete Author', year: 2024, isbn: '6666666666' });
      const bookId = createRes.body.id;

      const res = await request(`http://localhost:${testPort}`).delete(`/api/books/${bookId}`);
      expect(res.status).toBe(204);

      // Verify book is deleted
      const getRes = await request(`http://localhost:${testPort}`).get(`/api/books/${bookId}`);
      expect(getRes.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(`http://localhost:${testPort}`).delete('/api/books/99999');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Book not found');
    });
  });
});
