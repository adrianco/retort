import request from 'supertest';
import app from '../index';

describe('Book API', () => {
  beforeEach(async () => {
    // Clear database before each test
    const db = (app as any).db;
    if (db && db.db) {
      await db.db.exec('DELETE FROM books');
    }
  });

  describe('Health Check', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status', 'OK');
    });
  });

  describe('POST /books', () => {
    it('should create a new book with valid data', async () => {
      const bookData = {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0-7432-7356-5'
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.title).toBe(bookData.title);
      expect(response.body.author).toBe(bookData.author);
      expect(response.body.year).toBe(bookData.year);
      expect(response.body.isbn).toBe(bookData.isbn);
    });

    it('should reject book creation without title', async () => {
      const bookData = {
        author: 'F. Scott Fitzgerald'
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('error');
    });

    it('should reject book creation without author', async () => {
      const bookData = {
        title: 'The Great Gatsby'
      };

      const response = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(response.body).toHaveProperty('error');
    });
  });

  describe('GET /books', () => {
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

      const response = await request(app).get('/books').expect(200);
      
      expect(response.body).toHaveLength(2);
    });

    it('should filter books by author', async () => {
      // Create books with different authors
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
        .expect(200);
      
      expect(response.body).toHaveLength(1);
      expect(response.body[0].author).toBe('Author 1');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald'
      });
      
      const bookId = createResponse.body.id;
      
      const response = await request(app).get(`/books/${bookId}`).expect(200);
      
      expect(response.body.title).toBe('The Great Gatsby');
      expect(response.body.author).toBe('F. Scott Fitzgerald');
    });

    it('should return 404 for non-existent book', async () => {
      const response = await request(app).get('/books/999').expect(404);
      
      expect(response.body).toHaveProperty('error');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update an existing book', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald'
      });
      
      const bookId = createResponse.body.id;
      
      const updateData = {
        title: 'The Great Gatsby: Revised Edition',
        year: 1926
      };
      
      const response = await request(app)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200);
      
      expect(response.body.title).toBe(updateData.title);
      expect(response.body.year).toBe(updateData.year);
    });

    it('should return 404 for updating non-existent book', async () => {
      const updateData = {
        title: 'The Great Gatsby'
      };
      
      const response = await request(app)
        .put('/books/999')
        .send(updateData)
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete an existing book', async () => {
      // Create a book first
      const createResponse = await request(app).post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald'
      });
      
      const bookId = createResponse.body.id;
      
      const response = await request(app)
        .delete(`/books/${bookId}`)
        .expect(204);
      
      // Verify it's deleted by trying to fetch it
      await request(app).get(`/books/${bookId}`).expect(404);
    });

    it('should return 404 for deleting non-existent book', async () => {
      const response = await request(app)
        .delete('/books/999')
        .expect(404);
      
      expect(response.body).toHaveProperty('error');
    });
  });
});
