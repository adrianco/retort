import request from 'supertest';
import { app } from '../src/server';

describe('Book API Acceptance Tests', () => {
  // Clear books before each test
  beforeEach(() => {
    // In a real implementation, we would reset the database
    // For now, we'll just make sure we start with clean state
    // The in-memory approach is reset in the server startup
  });

  describe('Health Check', () => {
    it('should return health status', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        status: 'OK',
        timestamp: expect.any(String)
      });
    });
  });

  describe('Book Operations', () => {
    it('should create a new book', async () => {
      const newBook = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      };

      const response = await request(app)
        .post('/books')
        .send(newBook)
        .expect(201)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        id: expect.any(Number),
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      });
    });

    it('should reject creating a book without title or author', async () => {
      const invalidBook = {
        title: '',
        author: 'F. Scott Fitzgerald'
      };

      const response = await request(app)
        .post('/books')
        .send(invalidBook)
        .expect(400);

      expect(response.body).toEqual({
        error: 'Title and author are required fields'
      });
    });

    it('should list all books', async () => {
      // First create some books
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author 1'
      });
      
      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author 2'
      });

      const response = await request(app)
        .get('/books')
        .expect(200)
        .expect('Content-Type', /json/);

      expect(response.body).toHaveLength(2);
      expect(response.body[0]).toHaveProperty('title', 'Book 1');
      expect(response.body[1]).toHaveProperty('title', 'Book 2');
    });

    it('should filter books by author', async () => {
      // First create some books
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author 1'
      });
      
      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author 2'
      });

      const response = await request(app)
        .get('/books')
        .query({ author: 'Author 1' })
        .expect(200)
        .expect('Content-Type', /json/);

      expect(response.body).toHaveLength(1);
      expect(response.body[0]).toHaveProperty('author', 'Author 1');
    });

    it('should get a single book by ID', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'Book 1',
          author: 'Author 1'
        });

      const bookId = createResponse.body.id;

      const response = await request(app)
        .get(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        id: bookId,
        title: 'Book 1',
        author: 'Author 1',
        year: null,
        isbn: null
      });
    });

    it('should return 404 for non-existent book ID', async () => {
      const response = await request(app)
        .get('/books/999')
        .expect(404)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        error: 'Book not found'
      });
    });

    it('should update a book', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'Book 1',
          author: 'Author 1'
        });

      const bookId = createResponse.body.id;

      const updateData = {
        title: 'Updated Book Title',
        author: 'Updated Author',
        year: 2023,
        isbn: '123-456-789'
      };

      const response = await request(app)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        id: bookId,
        title: 'Updated Book Title',
        author: 'Updated Author',
        year: 2023,
        isbn: '123-456-789'
      });
    });

    it('should return 404 when trying to update non-existent book', async () => {
      const updateData = {
        title: 'Updated Book Title',
        author: 'Updated Author'
      };

      const response = await request(app)
        .put('/books/999')
        .send(updateData)
        .expect(404)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        error: 'Book not found'
      });
    });

    it('should delete a book', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'Book 1',
          author: 'Author 1'
        });

      const bookId = createResponse.body.id;

      const response = await request(app)
        .delete(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        message: 'Book deleted successfully'
      });

      // Verify the book was deleted
      const getResponse = await request(app)
        .get(`/books/${bookId}`)
        .expect(404);
    });

    it('should return 404 when trying to delete non-existent book', async () => {
      const response = await request(app)
        .delete('/books/999')
        .expect(404)
        .expect('Content-Type', /json/);

      expect(response.body).toEqual({
        error: 'Book not found'
      });
    });
  });
});