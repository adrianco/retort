const request = require('supertest');
const fs = require('fs');
const path = require('path');

// For simplicity, we'll test against the actual server
// The server will use books.db in the root directory

describe('Book API Acceptance Tests', () => {
  let app;
  let dbPath;

  beforeAll(() => {
    // Import the server app
    const server = require('../src/server');
    app = server.app;
    
    // Remove any existing database file
    dbPath = path.join(__dirname, '../books.db');
    try {
      fs.unlinkSync(dbPath);
    } catch (err) {
      // File doesn't exist, that's fine
    }
  });

  afterAll(() => {
    // Clean up database file
    try {
      fs.unlinkSync(dbPath);
    } catch (err) {
      // File doesn't exist, that's fine
    }
  });

  describe('Health Check', () => {
    test('should return health status', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        status: 'OK',
        message: 'Book API is running'
      });
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

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        id: expect.any(Number),
        title: bookData.title,
        author: bookData.author,
        year: bookData.year,
        isbn: bookData.isbn
      });
    });

    test('should reject book creation without required fields', async () => {
      const bookData = {
        title: 'The Great Gatsby'
        // Missing author
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        error: 'Title and author are required'
      });
    });

    test('should list all books', async () => {
      // First create some books
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2000,
        isbn: '123-456-789'
      });

      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2001,
        isbn: '123-456-790'
      });

      const response = await request(app)
        .get('/books')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toHaveLength(2);
      expect(response.body[0]).toEqual({
        id: expect.any(Number),
        title: 'Book 1',
        author: 'Author A',
        year: 2000,
        isbn: '123-456-789'
      });
      expect(response.body[1]).toEqual({
        id: expect.any(Number),
        title: 'Book 2',
        author: 'Author B',
        year: 2001,
        isbn: '123-456-790'
      });
    });

    test('should filter books by author', async () => {
      // First create some books
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2000,
        isbn: '123-456-789'
      });

      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2001,
        isbn: '123-456-790'
      });

      await request(app).post('/books').send({
        title: 'Book 3',
        author: 'Author A',
        year: 2002,
        isbn: '123-456-791'
      });

      const response = await request(app)
        .get('/books?author=Author A')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toHaveLength(2);
      expect(response.body[0].author).toBe('Author A');
      expect(response.body[1].author).toBe('Author A');
    });

    test('should get a single book by ID', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0-7432-7356-5'
        });

      const bookId = createResponse.body.id;

      const response = await request(app)
        .get(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        id: bookId,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      });
    });

    test('should return 404 for non-existent book', async () => {
      const response = await request(app)
        .get('/books/999')
        .expect(404)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        error: 'Book not found'
      });
    });

    test('should update a book', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0-7432-7356-5'
        });

      const bookId = createResponse.body.id;

      const updateData = {
        title: 'The Great Gatsby - Revised Edition',
        author: 'F. Scott Fitzgerald',
        year: 1926,
        isbn: '978-0-7432-7356-6'
      };

      const response = await request(app)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        id: bookId,
        title: updateData.title,
        author: updateData.author,
        year: updateData.year,
        isbn: updateData.isbn
      });
    });

    test('should return 404 when updating non-existent book', async () => {
      const updateData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
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

    test('should delete a book', async () => {
      // First create a book
      const createResponse = await request(app)
        .post('/books')
        .send({
          title: 'The Great Gatsby',
          author: 'F. Scott Fitzgerald',
          year: 1925,
          isbn: '978-0-7432-7356-5'
        });

      const bookId = createResponse.body.id;

      const response = await request(app)
        .delete(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        message: 'Book deleted successfully'
      });
    });

    test('should return 404 when deleting non-existent book', async () => {
      const response = await request(app)
        .delete('/books/999')
        .expect(404)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        error: 'Book not found'
      });
    });

    test('should reject duplicate ISBN', async () => {
      // First create a book with an ISBN
      await request(app)
        .post('/books')
        .send({
          title: 'Book 1',
          author: 'Author A',
          year: 2000,
          isbn: '123-456-789'
        });

      // Try to create another book with the same ISBN
      const response = await request(app)
        .post('/books')
        .send({
          title: 'Book 2',
          author: 'Author B',
          year: 2001,
          isbn: '123-456-789'
        })
        .expect(400)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({
        error: 'ISBN must be unique'
      });
    });
  });
});