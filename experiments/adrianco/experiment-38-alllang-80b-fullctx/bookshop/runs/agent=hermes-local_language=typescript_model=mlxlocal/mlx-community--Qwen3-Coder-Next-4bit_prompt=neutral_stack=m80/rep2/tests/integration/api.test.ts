import request from 'supertest';
import app from '../src/server';
import { BookDatabase } from '../src/database/database';

describe('Book API Integration Tests', () => {
  const testDb = new BookDatabase(':memory:');
  let server: any;

  beforeAll(async () => {
    await testDb.initialize();
    // Override the default db instance for testing
    jest.mock('../src/database/database', () => {
      const original = jest.requireActual('../src/database/database');
      return { ...original, BookDatabase: testDb };
    });
    server = app.listen(3001);
  });

  afterAll(async () => {
    await testDb.close();
    server.close();
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('healthy');
      expect(res.body).toHaveProperty('timestamp');
    });
  });

  describe('GET /books', () => {
    it('should return all books', async () => {
      // Create a test book first
      await testDb.createBook({
        title: 'Test Book',
        author: 'Test Author',
        year: 2024,
        isbn: '1234567890',
      });

      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('books');
      expect(res.body).toHaveProperty('count');
      expect(res.body.count).toBeGreaterThanOrEqual(1);
    });

    it('should filter books by author', async () => {
      await testDb.createBook({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '111',
      });
      await testDb.createBook({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '222',
      });

      const res = await request(app).get('/books?author=Author%20A');
      expect(res.status).toBe(200);
      expect(res.body.books.length).toBe(1);
      expect(res.body.books[0].author).toBe('Author A');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a single book by ID', async () => {
      const book = await testDb.createBook({
        title: 'Get Book',
        author: 'Get Author',
        year: 2022,
        isbn: '999',
      });

      const res = await request(app).get(`/books/${book.id}`);
      expect(res.status).toBe(200);
      expect(res.body.book).toHaveProperty('id', book.id);
      expect(res.body.book.title).toBe('Get Book');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/99999');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 400 for invalid book ID', async () => {
      const res = await request(app).get('/books/abc');
      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error');
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          title: 'New Book',
          author: 'New Author',
          year: 2024,
          isbn: '0000000001',
        });
      expect(res.status).toBe(201);
      expect(res.body.book).toHaveProperty('id');
      expect(res.body.book.title).toBe('New Book');
    });

    it('should require title', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          author: 'Some Author',
          year: 2024,
          isbn: '123',
        });
      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error');
    });

    it('should require author', async () => {
      const res = await request(app)
        .post('/books')
        .send({
          title: 'Some Title',
          year: 2024,
          isbn: '123',
        });
      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error');
    });

    it('should return 500 for internal server error', async () => {
      // Test with invalid data
      const res = await request(app)
        .post('/books')
        .send({});
      expect(res.status).toBe(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      const book = await testDb.createBook({
        title: 'Original Title',
        author: 'Original Author',
        year: 2020,
        isbn: '987',
      });

      const res = await request(app)
        .put(`/books/${book.id}`)
        .send({
          title: 'Updated Title',
          author: 'Updated Author',
        });
      expect(res.status).toBe(200);
      expect(res.body.book.title).toBe('Updated Title');
      expect(res.body.book.author).toBe('Updated Author');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/books/99999')
        .send({ title: 'Updated' });
      expect(res.status).toBe(404);
    });

    it('should return 400 for invalid book ID', async () => {
      const res = await request(app).put('/books/abc').send({});
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      const book = await testDb.createBook({
        title: 'To Delete',
        author: 'Delete Author',
        year: 2023,
        isbn: '555',
      });

      const res = await request(app).delete(`/books/${book.id}`);
      expect(res.status).toBe(204);

      // Verify deletion
      const getRes = await request(app).get(`/books/${book.id}`);
      expect(getRes.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/99999');
      expect(res.status).toBe(404);
    });

    it('should return 400 for invalid book ID', async () => {
      const res = await request(app).delete('/books/abc');
      expect(res.status).toBe(400);
    });
  });
});
