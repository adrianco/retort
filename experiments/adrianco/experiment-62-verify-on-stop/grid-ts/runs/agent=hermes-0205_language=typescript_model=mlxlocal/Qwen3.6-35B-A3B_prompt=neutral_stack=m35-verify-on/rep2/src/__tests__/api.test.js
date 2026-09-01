const request = require('supertest');
const { app } = require('../app.js');
const { closeDb, cleanDatabase } = require('../db.js');

const API_BASE = '/api';

describe('Book Collection API', () => {
  beforeEach(() => {
    // Clean the database using the same db instance the app uses
    cleanDatabase();
  });

  afterAll(() => {
    closeDb();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.statusCode).toBe(200);
      expect(res.body).toHaveProperty('status', 'ok');
      expect(res.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book and return 201', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };

      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send(bookData)
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe(bookData.title);
      expect(res.body.author).toBe(bookData.author);
      expect(res.body.year).toBe(bookData.year);
      expect(res.body.isbn).toBe(bookData.isbn);
      expect(res.body).toHaveProperty('created_at');
      expect(res.body).toHaveProperty('updated_at');
    });

    it('should return 400 when title is missing', async () => {
      const bookData = {
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };

      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send(bookData)
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(400);
      expect(res.body).toHaveProperty('error', 'Validation failed');
      expect(res.body.validation_errors).toBeDefined();
      expect(res.body.validation_errors.some(e => e.field === 'title')).toBe(true);
    });

    it('should return 400 when author is missing', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        year: 1925,
        isbn: '978-0743273565',
      };

      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send(bookData)
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(400);
      expect(res.body.validation_errors.some(e => e.field === 'author')).toBe(true);
    });

    it('should return 409 when ISBN already exists', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };

      await request(app)
        .post(`${API_BASE}/books`)
        .send(bookData)
        .set('Content-Type', 'application/json');

      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send(bookData)
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(409);
      expect(res.body).toHaveProperty('error', 'A book with this ISBN already exists');
    });
  });

  describe('GET /books', () => {
    it('should return all books', async () => {
      await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Book One',
          author: 'Author A',
          year: 2020,
          isbn: 'isbn-001',
        });

      await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Book Two',
          author: 'Author B',
          year: 2021,
          isbn: 'isbn-002',
        });

      const res = await request(app).get(`${API_BASE}/books`);

      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(2);
    });

    it('should filter books by author', async () => {
      await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Book One',
          author: 'Author A',
          year: 2020,
          isbn: 'isbn-001',
        });

      await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Book Two',
          author: 'Author A',
          year: 2021,
          isbn: 'isbn-002',
        });

      await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Book Three',
          author: 'Author B',
          year: 2022,
          isbn: 'isbn-003',
        });

      const res = await request(app).get(`${API_BASE}/books`).query({ author: 'Author A' });

      expect(res.statusCode).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(2);
      expect(res.body.every(b => b.author === 'Author A')).toBe(true);
    });

    it('should return empty array when no books exist', async () => {
      const res = await request(app).get(`${API_BASE}/books`);
      expect(res.statusCode).toBe(200);
      expect(res.body).toEqual([]);
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by id', async () => {
      const createRes = await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Test Book',
          author: 'Test Author',
          year: 2023,
          isbn: 'isbn-test-001',
        });

      const bookId = createRes.body.id;

      const getRes = await request(app).get(`${API_BASE}/books/${bookId}`);

      expect(getRes.statusCode).toBe(200);
      expect(getRes.body.id).toBe(bookId);
      expect(getRes.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get(`${API_BASE}/books/9999`);
      expect(res.statusCode).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });

    it('should return 400 for invalid id', async () => {
      const res = await request(app).get(`${API_BASE}/books/abc`);
      expect(res.statusCode).toBe(400);
      expect(res.body).toHaveProperty('error', 'Invalid book ID');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book and return 200', async () => {
      const createRes = await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Original Title',
          author: 'Original Author',
          year: 2020,
          isbn: 'isbn-update-001',
        });

      const bookId = createRes.body.id;

      const updateRes = await request(app)
        .put(`${API_BASE}/books/${bookId}`)
        .send({
          title: 'Updated Title',
          year: 2023,
        });

      expect(updateRes.statusCode).toBe(200);
      expect(updateRes.body.title).toBe('Updated Title');
      expect(updateRes.body.author).toBe('Original Author');
      expect(updateRes.body.year).toBe(2023);
    });

    it('should return 404 when updating non-existent book', async () => {
      const res = await request(app)
        .put(`${API_BASE}/books/9999`)
        .send({ title: 'Nonexistent' });

      expect(res.statusCode).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });

    it('should return 400 for invalid update data', async () => {
      const createRes = await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Original Title',
          author: 'Original Author',
          year: 2020,
          isbn: 'isbn-update-002',
        });

      const bookId = createRes.body.id;

      const res = await request(app)
        .put(`${API_BASE}/books/${bookId}`)
        .send({ title: '' });

      expect(res.statusCode).toBe(400);
      expect(res.body.validation_errors.some(e => e.field === 'title')).toBe(true);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book and return 204', async () => {
      const createRes = await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'To Delete',
          author: 'Delete Author',
          year: 2021,
          isbn: 'isbn-delete-001',
        });

      const bookId = createRes.body.id;

      const res = await request(app).delete(`${API_BASE}/books/${bookId}`);
      expect(res.statusCode).toBe(204);

      // Verify it's actually gone
      const getRes = await request(app).get(`${API_BASE}/books/${bookId}`);
      expect(getRes.statusCode).toBe(404);
    });

    it('should return 404 when deleting non-existent book', async () => {
      const res = await request(app).delete(`${API_BASE}/books/9999`);
      expect(res.statusCode).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });
  });

  describe('Validation edge cases', () => {
    it('should reject POST with empty body', async () => {
      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send({})
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(400);
      expect(res.body.validation_errors.length).toBeGreaterThan(0);
    });

    it('should reject POST with non-integer year', async () => {
      const res = await request(app)
        .post(`${API_BASE}/books`)
        .send({
          title: 'Test',
          author: 'Test Author',
          year: 20.5,
          isbn: 'isbn-year-test',
        })
        .set('Content-Type', 'application/json');

      expect(res.statusCode).toBe(400);
      expect(res.body.validation_errors.some(e => e.field === 'year')).toBe(true);
    });
  });
});
