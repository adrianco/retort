// Acceptance Tests for Book Collection API
const request = require('supertest');
const { app } = require('../src/server');

// Create a test server instance
const server = app;

// Test suite
describe('Book Collection API', () => {
  beforeEach(() => {
    // Reset the in-memory storage for each test
    // In a real implementation, we'd reset the database
  });

  describe('Health Check', () => {
    test('should return health status', async () => {
      const response = await request(server).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'OK');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('Book Management', () => {
    test('should create a new book', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      };

      const response = await request(server)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(response.body).toHaveProperty('title', bookData.title);
      expect(response.body).toHaveProperty('author', bookData.author);
      expect(response.body).toHaveProperty('year', bookData.year);
      expect(response.body).toHaveProperty('isbn', bookData.isbn);
      expect(response.body).toHaveProperty('id');
    });

    test('should reject creating a book without title or author', async () => {
      const bookData = {
        title: '',
        author: 'Test Author'
      };

      const response = await request(server)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('error', 'Title and author are required');
    });

    test('should list all books', async () => {
      // Add some test books
      await request(server).post('/books').send({
        title: 'Book 1',
        author: 'Author 1'
      });
      
      await request(server).post('/books').send({
        title: 'Book 2',
        author: 'Author 2'
      });

      const response = await request(server).get('/books').expect(200);

      expect(response.body).toHaveLength(2);
      expect(response.body[0]).toHaveProperty('title', 'Book 1');
      expect(response.body[1]).toHaveProperty('title', 'Book 2');
    });

    test('should filter books by author', async () => {
      // Add some test books
      await request(server).post('/books').send({
        title: 'Book 1',
        author: 'Author 1'
      });
      
      await request(server).post('/books').send({
        title: 'Book 2',
        author: 'Author 2'
      });

      const response = await request(server).get('/books?author=Author%201').expect(200);

      expect(response.body).toHaveLength(1);
      expect(response.body[0]).toHaveProperty('author', 'Author 1');
    });

    test('should get a single book by ID', async () => {
      // Create a book first
      const createResponse = await request(server).post('/books').send({
        title: 'Test Book',
        author: 'Test Author'
      });

      const bookId = createResponse.body.id;
      const response = await request(server).get(`/books/${bookId}`).expect(200);

      expect(response.body).toHaveProperty('id', bookId);
      expect(response.body).toHaveProperty('title', 'Test Book');
      expect(response.body).toHaveProperty('author', 'Test Author');
    });

    test('should return 404 for non-existent book', async () => {
      const response = await request(server).get('/books/999').expect(404);
      expect(response.body).toHaveProperty('error', 'Book not found');
    });

    test('should update a book', async () => {
      // Create a book first
      const createResponse = await request(server).post('/books').send({
        title: 'Original Title',
        author: 'Original Author'
      });

      const bookId = createResponse.body.id;
      
      const updateData = {
        title: 'Updated Title',
        author: 'Updated Author',
        year: 2023
      };

      const response = await request(server)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200);

      expect(response.body).toHaveProperty('title', updateData.title);
      expect(response.body).toHaveProperty('author', updateData.author);
      expect(response.body).toHaveProperty('year', updateData.year);
    });

    test('should return 404 when updating non-existent book', async () => {
      const updateData = {
        title: 'Updated Title',
        author: 'Updated Author'
      };

      const response = await request(server)
        .put('/books/999')
        .send(updateData)
        .expect(404);

      expect(response.body).toHaveProperty('error', 'Book not found');
    });

    test('should delete a book', async () => {
      // Create a book first
      const createResponse = await request(server).post('/books').send({
        title: 'To Delete',
        author: 'Test Author'
      });

      const bookId = createResponse.body.id;
      
      const response = await request(server)
        .delete(`/books/${bookId}`)
        .expect(200);

      expect(response.body).toHaveProperty('message', 'Book deleted successfully');
      
      // Verify the book is deleted
      const getResponse = await request(server).get(`/books/${bookId}`).expect(404);
      expect(getResponse.body).toHaveProperty('error', 'Book not found');
    });

    test('should return 404 when deleting non-existent book', async () => {
      const response = await request(server)
        .delete('/books/999')
        .expect(404);

      expect(response.body).toHaveProperty('error', 'Book not found');
    });
  });
});

// Export for potential reuse
module.exports = { app };