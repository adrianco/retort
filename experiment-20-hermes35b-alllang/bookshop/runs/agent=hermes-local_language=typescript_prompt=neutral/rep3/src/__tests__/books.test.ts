import request from 'supertest';
import { app } from '../server';
import { closeDatabase, getAllBooks, createBook as createBookDb, deleteBook as deleteBookDb } from '../db';

const BASE_URL = '/';

describe('Book API Integration Tests', () => {
  // Clean up database before each test
  beforeEach(() => {
    const books = getAllBooks();
    books.forEach((book) => {
      deleteBookDb(book.id);
    });
  });

  // Clean up database after all tests
  afterAll(() => {
    closeDatabase();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const response = await request(app).get(`${BASE_URL}health`).expect(200);
      expect(response.body.status).toBe('ok');
      expect(response.body.timestamp).toBeDefined();
    });
  });

  describe('POST /books', () => {
    it('should create a new book with all fields and return 201', async () => {
      const response = await request(app)
        .post(`${BASE_URL}books`)
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0743273565',
        })
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.title).toBe('The Great Gatsby');
      expect(response.body.author).toBe('F. Scott Fitzgerald');
      expect(response.body.year).toBe(1925);
      expect(response.body.isbn).toBe('978-0743273565');
    });

    it('should create a book without optional fields and return 201', async () => {
      const response = await request(app)
        .post(`${BASE_URL}books`)
        .send({
          title: 'Simple Book',
          author: 'Test Author',
        })
        .expect(201);

      expect(response.body.title).toBe('Simple Book');
      expect(response.body.author).toBe('Test Author');
      expect(response.body.year).toBeNull();
      expect(response.body.isbn).toBeNull();
    });

    it('should return 400 when title is missing', async () => {
      const response = await request(app)
        .post(`${BASE_URL}books`)
        .send({
          author: 'Test Author',
        })
        .expect(400);

      expect(response.body.errors).toBeDefined();
      expect(response.body.errors).toContain('Title is required and must be a non-empty string');
    });

    it('should return 400 when author is missing', async () => {
      const response = await request(app)
        .post(`${BASE_URL}books`)
        .send({
          title: 'Test Book',
        })
        .expect(400);

      expect(response.body.errors).toBeDefined();
      expect(response.body.errors).toContain('Author is required and must be a non-empty string');
    });

    it('should return 400 when both title and author are missing', async () => {
      const response = await request(app)
        .post(`${BASE_URL}books`)
        .send({})
        .expect(400);

      expect(response.body.errors).toHaveLength(2);
    });
  });

  describe('GET /books', () => {
    it('should return an empty list when no books exist', async () => {
      const response = await request(app)
        .get(`${BASE_URL}books`)
        .expect(200);

      expect(response.body).toEqual([]);
    });

    it('should return all books', async () => {
      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book One', author: 'Author A', year: 2020 });

      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book Two', author: 'Author B', year: 2021 });

      const response = await request(app)
        .get(`${BASE_URL}books`)
        .expect(200);

      expect(response.body).toHaveLength(2);
      expect(response.body[0].title).toBe('Book One');
      expect(response.body[1].title).toBe('Book Two');
    });

    it('should filter books by author query param', async () => {
      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book One', author: 'Author A', year: 2020 });

      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book Two', author: 'Author A', year: 2021 });

      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book Three', author: 'Author B', year: 2022 });

      const response = await request(app)
        .get(`${BASE_URL}books`)
        .query({ author: 'Author A' })
        .expect(200);

      expect(response.body).toHaveLength(2);
      expect(response.body.every((book: { author: string }) => book.author === 'Author A')).toBe(true);
    });

    it('should return empty array for non-matching author filter', async () => {
      await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Book One', author: 'Author A', year: 2020 });

      const response = await request(app)
        .get(`${BASE_URL}books`)
        .query({ author: 'Nonexistent' })
        .expect(200);

      expect(response.body).toHaveLength(0);
    });
  });

  describe('GET /books/:id', () => {
    it('should return a single book by ID', async () => {
      const createResponse = await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Test Book', author: 'Test Author', year: 2023, isbn: '123-456' })
        .expect(201);

      const response = await request(app)
        .get(`${BASE_URL}books/${createResponse.body.id}`)
        .expect(200);

      expect(response.body.id).toBe(createResponse.body.id);
      expect(response.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book ID', async () => {
      await request(app)
        .get(`${BASE_URL}books/9999`)
        .expect(404);
    });

    it('should return 400 for invalid book ID', async () => {
      await request(app)
        .get(`${BASE_URL}books/abc`)
        .expect(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book and return the updated object', async () => {
      const createResponse = await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Original Title', author: 'Original Author' })
        .expect(201);

      const response = await request(app)
        .put(`${BASE_URL}books/${createResponse.body.id}`)
        .send({ title: 'Updated Title', author: 'Updated Author', year: 2024 })
        .expect(200);

      expect(response.body.title).toBe('Updated Title');
      expect(response.body.author).toBe('Updated Author');
      expect(response.body.year).toBe(2024);
    });

    it('should return 404 for updating a non-existent book', async () => {
      await request(app)
        .put(`${BASE_URL}books/9999`)
        .send({ title: 'Non-existent' })
        .expect(404);
    });

    it('should return 400 when updating with invalid data (missing title)', async () => {
      const createResponse = await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'Original', author: 'Original Author' })
        .expect(201);

      await request(app)
        .put(`${BASE_URL}books/${createResponse.body.id}`)
        .send({ author: 'New Author' })
        .expect(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book and return 204', async () => {
      const createResponse = await request(app)
        .post(`${BASE_URL}books`)
        .send({ title: 'To Delete', author: 'Author' })
        .expect(201);

      await request(app)
        .delete(`${BASE_URL}books/${createResponse.body.id}`)
        .expect(204);

      // Verify it's gone
      await request(app)
        .get(`${BASE_URL}books/${createResponse.body.id}`)
        .expect(404);
    });

    it('should return 404 when deleting a non-existent book', async () => {
      await request(app)
        .delete(`${BASE_URL}books/9999`)
        .expect(404);
    });
  });
});
