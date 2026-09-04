import request from 'supertest';
import app from './src/server';

describe('Book API', () => {
  // Clean up the database before tests
  beforeAll((done) => {
    done();
  });

  // Clean up the database after tests
  afterAll((done) => {
    done();
  });

  it('should return health status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'OK' });
  });

  it('should create a new book', async () => {
    const response = await request(app)
      .post('/books')
      .send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
    
    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('id');
  });

  it('should get all books', async () => {
    const response = await request(app).get('/books');
    expect(response.status).toBe(200);
    expect(response.body).toBeInstanceOf(Array);
  });

  it('should get a single book by ID', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
    
    const bookId = createResponse.body.id;
    
    const response = await request(app).get(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('id', bookId);
  });

  it('should update a book', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
    
    const bookId = createResponse.body.id;
    
    const response = await request(app)
      .put(`/books/${bookId}`)
      .send({
        title: 'Updated Test Book',
        author: 'Updated Test Author',
        year: 2024,
        isbn: '0987654321'
      });
    
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ message: 'Book updated successfully' });
  });

  it('should delete a book', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890'
      });
    
    const bookId = createResponse.body.id;
    
    const response = await request(app).delete(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ message: 'Book deleted successfully' });
  });

  it('should return 404 for non-existent book', async () => {
    const response = await request(app).get('/books/99999');
    expect(response.status).toBe(404);
  });

  it('should return 400 for invalid book ID', async () => {
    const response = await request(app).get('/books/abc');
    expect(response.status).toBe(400);
  });

  it('should filter books by author', async () => {
    const response = await request(app).get('/books').query({ author: 'Test Author' });
    expect(response.status).toBe(200);
  });
});