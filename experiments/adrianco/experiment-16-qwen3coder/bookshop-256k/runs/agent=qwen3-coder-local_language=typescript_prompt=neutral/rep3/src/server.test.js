const request = require('supertest');
const app = require('./server');

describe('Book API', () => {
  // Test health endpoint
  describe('GET /health', () => {
    it('should return health status', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('status', 'OK');
      expect(res.body).toHaveProperty('message', 'Book API is running');
    });
  });

  // Test book operations
  describe('Book Operations', () => {
    let createdBookId;

    // Test POST /books
    it('should create a new book', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      };

      const res = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(res.body).toHaveProperty('title', bookData.title);
      expect(res.body).toHaveProperty('author', bookData.author);
      expect(res.body).toHaveProperty('year', bookData.year);
      expect(res.body).toHaveProperty('isbn', bookData.isbn);
      expect(res.body).toHaveProperty('id');
      
      createdBookId = res.body.id;
    });

    // Test POST /books with missing required fields
    it('should return error for missing required fields', async () => {
      const bookData = {
        title: 'Another Book',
        // Missing author
      };

      const res = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(res.body).toHaveProperty('error', 'Title and author are required fields');
    });

    // Test GET /books
    it('should list all books', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
    });

    // Test GET /books with author filter
    it('should filter books by author', async () => {
      const res = await request(app).get('/books?author=F. Scott Fitzgerald');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      if (res.body.length > 0) {
        expect(res.body[0]).toHaveProperty('author', 'F. Scott Fitzgerald');
      }
    });

    // Test GET /books/:id
    it('should get a single book by ID', async () => {
      const res = await request(app).get(`/books/${createdBookId}`);
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('id', createdBookId);
      expect(res.body).toHaveProperty('title', 'The Great Gatsby');
    });

    // Test GET /books/:id for non-existent book
    it('should return error for non-existent book', async () => {
      const res = await request(app).get('/books/99999');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });

    // Test PUT /books/:id
    it('should update a book', async () => {
      const updatedData = {
        title: 'The Great Gatsby - Updated',
        author: 'F. Scott Fitzgerald',
        year: 1926,
        isbn: '978-0-7432-7356-6'
      };

      const res = await request(app)
        .put(`/books/${createdBookId}`)
        .send(updatedData)
        .expect(200);

      expect(res.body).toHaveProperty('title', updatedData.title);
      expect(res.body).toHaveProperty('author', updatedData.author);
      expect(res.body).toHaveProperty('year', updatedData.year);
      expect(res.body).toHaveProperty('isbn', updatedData.isbn);
    });

    // Test PUT /books/:id with missing required fields
    it('should return error when updating with missing required fields', async () => {
      const updatedData = {
        title: 'Another Book',
        // Missing author
      };

      const res = await request(app)
        .put(`/books/${createdBookId}`)
        .send(updatedData)
        .expect(400);

      expect(res.body).toHaveProperty('error', 'Title and author are required fields');
    });

    // Test DELETE /books/:id
    it('should delete a book', async () => {
      const res = await request(app).delete(`/books/${createdBookId}`);
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('message', 'Book deleted successfully');
    });

    // Test DELETE /books/:id for non-existent book
    it('should return error for deleting non-existent book', async () => {
      const res = await request(app).delete('/books/99999');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });
  });
});