import request from 'supertest';

describe('Book API Integration Tests', () => {
  let app: any;

  beforeAll(() => {
    // Use in-memory database for testing
    process.env.DB_PATH = ':memory:';
    // Clear all cached modules
    const cacheModulePaths = Object.keys(require.cache);
    cacheModulePaths.forEach((path) => {
      if (path.includes('src') || path.includes('database')) {
        delete require.cache[require.resolve(path)];
      }
    });
    
    // Import fresh app
    const appModule = require('../src/app');
    app = appModule.default;
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'ok');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(response.body).toMatchObject({
        title: bookData.title,
        author: bookData.author,
        year: bookData.year,
        isbn: bookData.isbn,
        id: expect.any(Number),
      });
      expect(response.body).toHaveProperty('createdAt');
      expect(response.body).toHaveProperty('updatedAt');
    });

    it('should return 400 for missing title', async () => {
      const bookData = {
        author: 'Some Author',
        year: 2023,
        isbn: '1234567890',
      };

      const response = await request(app).post('/books').send(bookData);
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Validation failed');
    });

    it('should return 400 for missing author', async () => {
      const bookData = {
        title: 'Some Book',
        year: 2023,
        isbn: '1234567890',
      };

      const response = await request(app).post('/books').send(bookData);
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Validation failed');
    });

    it('should return 400 for invalid year', async () => {
      const bookData = {
        title: 'Some Book',
        author: 'Some Author',
        year: -1,
        isbn: '1234567890',
      };

      const response = await request(app).post('/books').send(bookData);
      expect(response.status).toBe(400);
      expect(response.body.error).toBe('Validation failed');
    });
  });

  describe('GET /books', () => {
    it('should list all books', async () => {
      // Create 2 books in this test only
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '111',
      });

      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '222',
      });

      const response = await request(app).get('/books');
      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body.length).toBe(2);
    });

    it('should filter by author', async () => {
      // Create 2 books in this test only
      await request(app).post('/books').send({
        title: 'Book 1',
        author: 'Author A',
        year: 2020,
        isbn: '111',
      });

      await request(app).post('/books').send({
        title: 'Book 2',
        author: 'Author B',
        year: 2021,
        isbn: '222',
      });

      const response = await request(app).get('/books?author=Author A');
      expect(response.status).toBe(200);
      expect(response.body.length).toBe(1);
      expect(response.body[0].author).toBe('Author A');
    });
  });

  describe('GET /books/:id', () => {
    it('should get a single book by id', async () => {
      const createResponse = await request(app).post('/books').send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890',
      });

      const bookId = createResponse.body.id;

      const response = await request(app).get(`/books/${bookId}`);
      expect(response.status).toBe(200);
      expect(response.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/999');
      expect(response.status).toBe(404);
      expect(response.body.error).toBe('Book not found');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      const createResponse = await request(app).post('/books').send({
        title: 'Original Title',
        author: 'Original Author',
        year: 2020,
        isbn: '111',
      });

      const bookId = createResponse.body.id;

      const response = await request(app)
        .put(`/books/${bookId}`)
        .send({
          title: 'Updated Title',
          year: 2021,
        });

      expect(response.status).toBe(200);
      expect(response.body.title).toBe('Updated Title');
      expect(response.body.author).toBe('Original Author');
      expect(response.body.year).toBe(2021);
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).put('/books/999').send({
        title: 'Updated Title',
      });
      expect(response.status).toBe(404);
      expect(response.body.error).toBe('Book not found');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      const createResponse = await request(app).post('/books').send({
        title: 'To Delete',
        author: 'Delete Author',
        year: 2020,
        isbn: '111',
      });

      const bookId = createResponse.body.id;

      const deleteResponse = await request(app).delete(`/books/${bookId}`);
      expect(deleteResponse.status).toBe(204);

      const getResponse = await request(app).get(`/books/${bookId}`);
      expect(getResponse.status).toBe(404);
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).delete('/books/999');
      expect(response.status).toBe(404);
      expect(response.body.error).toBe('Book not found');
    });
  });
});
