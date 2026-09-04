const request = require('supertest');
const app = require('./server');

// For testing, let's create a new server instance on a different port to avoid conflicts
const testApp = app;

describe('Book API', () => {
  // Clear database before each test - in a real app, we would reset the database
  beforeEach((done) => {
    // For file-based SQLite, we can just proceed with tests
    done();
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(testApp)
        .get('/health')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toEqual({ status: 'healthy' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      };

      const response = await request(testApp)
        .post('/books')
        .send(bookData)
        .expect(201)
        .expect('Content-Type', /json/);
      
      expect(response.body).toHaveProperty('id');
      expect(response.body.title).toBe(bookData.title);
      expect(response.body.author).toBe(bookData.author);
      expect(response.body.year).toBe(bookData.year);
      expect(response.body.isbn).toBe(bookData.isbn);
    });

    it('should return 400 if title is missing', async () => {
      const bookData = {
        author: 'F. Scott Fitzgerald'
      };

      const response = await request(testApp)
        .post('/books')
        .send(bookData)
        .expect(400);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('required fields');
    });

    it('should return 400 if author is missing', async () => {
      const bookData = {
        title: 'The Great Gatsby'
      };

      const response = await request(testApp)
        .post('/books')
        .send(bookData)
        .expect(400);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('required fields');
    });
  });

  describe('GET /books', () => {
    it('should return all books', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      await request(testApp)
        .post('/books')
        .send(bookData);

      const response = await request(testApp)
        .get('/books')
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBeGreaterThan(0);
      expect(response.body[0]).toHaveProperty('title');
      expect(response.body[0]).toHaveProperty('author');
    });

    it('should filter books by author', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      await request(testApp)
        .post('/books')
        .send(bookData);

      const response = await request(testApp)
        .get('/books')
        .query({ author: 'F. Scott Fitzgerald' })
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBeGreaterThan(0);
      expect(response.body[0].author).toBe('F. Scott Fitzgerald');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      const createResponse = await request(testApp)
        .post('/books')
        .send(bookData);
      
      const bookId = createResponse.body.id;

      const response = await request(testApp)
        .get(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body.title).toBe(bookData.title);
      expect(response.body.author).toBe(bookData.author);
      expect(response.body.year).toBe(bookData.year);
    });

    it('should return 404 if book does not exist', async () => {
      const response = await request(testApp)
        .get('/books/999999')
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Book not found');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book by ID', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      const createResponse = await request(testApp)
        .post('/books')
        .send(bookData);
      
      const bookId = createResponse.body.id;

      const updateData = {
        title: 'The Great Gatsby - Updated',
        author: 'F. Scott Fitzgerald',
        year: 1926,
        isbn: '978-0-7432-7356-6'
      };

      const response = await request(testApp)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body.title).toBe(updateData.title);
      expect(response.body.author).toBe(updateData.author);
      expect(response.body.year).toBe(updateData.year);
      expect(response.body.isbn).toBe(updateData.isbn);
    });

    it('should return 404 if trying to update non-existent book', async () => {
      const updateData = {
        title: 'The Great Gatsby - Updated',
        author: 'F. Scott Fitzgerald',
        year: 1926
      };

      const response = await request(testApp)
        .put('/books/999999')
        .send(updateData)
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Book not found');
    });

    it('should return 400 if title or author is missing during update', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      const createResponse = await request(testApp)
        .post('/books')
        .send(bookData);
      
      const bookId = createResponse.body.id;

      const updateData = {
        author: 'F. Scott Fitzgerald'
      };

      const response = await request(testApp)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(400);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('required fields');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book by ID', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      };

      // Create a book first
      const createResponse = await request(testApp)
        .post('/books')
        .send(bookData);
      
      const bookId = createResponse.body.id;

      const response = await request(testApp)
        .delete(`/books/${bookId}`)
        .expect(200)
        .expect('Content-Type', /json/);
      
      expect(response.body).toHaveProperty('message');
      expect(response.body.message).toContain('deleted');
    });

    it('should return 404 if trying to delete non-existent book', async () => {
      const response = await request(testApp)
        .delete('/books/999999')
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Book not found');
    });
  });

  describe('404 handling', () => {
    it('should return 404 for undefined routes', async () => {
      const response = await request(testApp)
        .get('/undefined-route')
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Endpoint not found');
    });
  });
});