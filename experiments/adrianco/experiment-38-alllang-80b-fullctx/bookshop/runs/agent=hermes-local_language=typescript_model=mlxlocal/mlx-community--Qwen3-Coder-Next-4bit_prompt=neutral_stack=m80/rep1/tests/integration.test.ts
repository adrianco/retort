import { createApp } from '../src/server';
import request from 'supertest';
const fs = require('fs');

describe('Book API Integration Tests', () => {
  let app: any;
  let server: any;
  let testDbPath: string;

  beforeAll(() => {
    // Create a unique database path for integration tests
    const timestamp = Date.now();
    testDbPath = `./books_integration_${timestamp}.db`;
    
    // Create the app
    app = createApp();
    
    // Replace the database service in the app with our test version
    const bookService = app.get('bookService');
    if (bookService) {
      const dbModule = require('../src/database');
      const TestDatabaseService = class TestDatabaseService extends dbModule.DatabaseService {
        constructor() {
          super(testDbPath);
        }
      };
      bookService.database = new TestDatabaseService();
    }
    
    server = app.listen(3001); // Use a different port for tests
  });

  afterAll(async () => {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    // Clean up test database
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  beforeEach(async () => {
    // Clear database before each test
    if (fs.existsSync(testDbPath)) {
      fs.unlinkSync(testDbPath);
    }
  });

  describe('Health Check', () => {
    it('should return healthy status', async () => {
      const res = await request(server).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('healthy');
      expect(res.body.timestamp).toBeDefined();
    });
  });

  describe('Books CRUD Operations', () => {
    let createdBookId: string;

    it('should create a new book', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      };

      const res = await request(server)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(res.body.book).toBeDefined();
      expect(res.body.book.title).toBe(bookData.title);
      expect(res.body.book.author).toBe(bookData.author);
      expect(res.body.book.year).toBe(bookData.year);
      expect(res.body.book.isbn).toBe(bookData.isbn);
      expect(res.body.book.id).toBeDefined();
      
      createdBookId = res.body.book.id;
    });

    it('should return 400 if required fields are missing', async () => {
      const res = await request(server)
        .post('/books')
        .send({
          title: 'Test Book'
          // Missing author, year, isbn
        })
        .expect(400);

      expect(res.body.error).toBeDefined();
    });

    it('should list all books', async () => {
      const res = await request(server).get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body.books)).toBe(true);
      expect(res.body.books.length).toBeGreaterThan(0);
    });

    it('should get a single book by ID', async () => {
      const res = await request(server).get(`/books/${createdBookId}`);
      expect(res.status).toBe(200);
      expect(res.body.book).toBeDefined();
      expect(res.body.book.id).toBe(createdBookId);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(server).get('/books/non-existent-id');
      expect(res.status).toBe(404);
    });

    it('should update a book', async () => {
      const updateData = {
        title: 'The Great Gatsby (Updated)',
        year: 1926
      };

      const res = await request(server)
        .put(`/books/${createdBookId}`)
        .send(updateData)
        .expect(200);

      expect(res.body.book.title).toBe(updateData.title);
      expect(res.body.book.year).toBe(updateData.year);
      // Author should remain unchanged
      expect(res.body.book.author).toBe('F. Scott Fitzgerald');
    });

    it('should return 404 when updating non-existent book', async () => {
      const res = await request(server)
        .put('/books/non-existent-id')
        .send({ title: 'Test' })
        .expect(404);
    });

    it('should delete a book', async () => {
      await request(server).delete(`/books/${createdBookId}`).expect(204);

      // Verify book is deleted
      const getRes = await request(server).get(`/books/${createdBookId}`);
      expect(getRes.status).toBe(404);
    });

    it('should return 404 when deleting non-existent book', async () => {
      const res = await request(server).delete('/books/non-existent-id');
      expect(res.status).toBe(404);
    });
  });

  describe('Filtering by Author', () => {
    beforeEach(async () => {
      await request(server).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2000,
        isbn: '111-1111111111'
      });

      await request(server).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2001,
        isbn: '222-2222222222'
      });
    });

    it('should filter books by author', async () => {
      const res = await request(server).get('/books?author=Author%20A');
      expect(res.status).toBe(200);
      expect(res.body.books.length).toBe(1);
      expect(res.body.books[0].author).toBe('Author A');
    });

    it('should return all books when no filter is provided', async () => {
      const res = await request(server).get('/books');
      expect(res.status).toBe(200);
      expect(res.body.books.length).toBeGreaterThan(1);
    });
  });
});
