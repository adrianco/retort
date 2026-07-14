process.env.DB_PATH = ':memory:';

import request from 'supertest';
import { app, db } from '../src/app';

describe('Book API', () => {
  beforeAll(async () => {
    // Database is already initialized when app.ts is imported
  });

  beforeEach(async () => {
    // Clear all books before each test to ensure isolation
    await db.clearAllBooks();
  });

  afterAll(async () => {
    await db.close();
  });

  describe('POST /books', () => {
    it('should create a new book with all fields', async () => {
      const response = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0743273565'
        });

      expect(response.status).toBe(201);
      expect(response.body).toMatchObject({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      });
      expect(response.body.id).toBeDefined();
    });

    it('should return 400 when title is missing', async () => {
      const response = await request(app)
        .post('/books')
        .send({
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0743273565'
        });
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Title is required');
    });

    it('should return 400 when author is missing', async () => {
      const response = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          year: 1925,
          isbn: '978-0743273565'
        });
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Author is required');
    });

    it('should return 400 when year is missing', async () => {
      const response = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          isbn: '978-0743273565'
        });
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Year is required and must be an integer');
    });

    it('should return 409 when ISBN is duplicate', async () => {
      await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      });
      const response = await request(app).post('/books').send({
        title: 'Another Book',
        author: 'Another Author',
        year: 2000,
        isbn: '978-0743273565'
      });
      expect(response.status).toBe(409);
      expect(response.body.error).toBe('A book with this ISBN already exists');
    });
  });

  describe('GET /books', () => {
    it('should return empty list when no books exist', async () => {
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(response.body).toEqual([]);
    });

    it('should return all books', async () => {
      await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      });
      await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(response.body).toHaveLength(2);
    });

    it('should filter books by author', async () => {
      await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      });
      await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
      const response = await request(app).get('/books').query({ author: 'George Orwell' });
      expect(response.status).toBe(200);
      expect(response.body).toHaveLength(1);
      expect(response.body[0].author).toBe('George Orwell');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      const createRes = await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
      const id = createRes.body.id;

      const response = await request(app).get(`/books/${id}`);
      expect(response.status).toBe(200);
      expect(response.body).toMatchObject({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/9999');
      expect(response.status).toBe(404);
      expect(response.body.error).toBe('Book not found');
    });

    it('should return 400 for invalid ID', async () => {
      const response = await request(app).get('/books/abc');
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book partially', async () => {
      const createRes = await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
      const id = createRes.body.id;

      const response = await request(app)
        .put(`/books/${id}`)
        .send({ title: 'Nineteen Eighty-Four' });

      expect(response.status).toBe(200);
      expect(response.body.title).toBe('Nineteen Eighty-Four');
      expect(response.body.author).toBe('George Orwell'); // unchanged
    });

    it('should return 404 when updating non-existent book', async () => {
      const response = await request(app)
        .put('/books/9999')
        .send({ title: 'Nonexistent' });
      expect(response.status).toBe(404);
    });

    it('should return 400 when no fields to update', async () => {
      const response = await request(app).put('/books/1').send({});
      expect(response.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      const createRes = await request(app).post('/books').send({
        title: '1984',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0451524935'
      });
      const id = createRes.body.id;

      const response = await request(app).delete(`/books/${id}`);
      expect(response.status).toBe(200);
      expect(response.body.message).toBe('Book deleted successfully');

      // Verify deletion
      const getResponse = await request(app).get(`/books/${id}`);
      expect(getResponse.status).toBe(404);
    });

    it('should return 404 when deleting non-existent book', async () => {
      const response = await request(app).delete('/books/9999');
      expect(response.status).toBe(404);
    });
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body.status).toBe('ok');
      expect(response.body.timestamp).toBeDefined();
    });
  });
});
