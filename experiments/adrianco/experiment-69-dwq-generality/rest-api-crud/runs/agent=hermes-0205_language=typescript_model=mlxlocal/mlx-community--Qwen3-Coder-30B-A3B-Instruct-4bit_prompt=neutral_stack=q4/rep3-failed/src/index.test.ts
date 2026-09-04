import request from 'supertest';
import app from './index';

describe('Book API', () => {
  // Clear database between tests
  beforeEach((done) => {
    const db = new (require('sqlite3').Database)(':memory');
    db.serialize(() => {
      db.run('CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT UNIQUE)');
      db.run('DELETE FROM books');
    });
    done();
  });

  it('should create a new book', async () => {
    const response = await request(app).post('/books').send({
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
    expect(response.body).toHaveProperty('books');
  });

  it('should get a single book by ID', async () => {
    const createResponse = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 2023,
      isbn: '1234567890'
    });

    const response = await request(app).get(`/books/${createResponse.body.id}`);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('title', 'Test Book');
  });

  it('should update a book', async () => {
    const createResponse = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 2023,
      isbn: '1234567890'
    });

    const response = await request(app).put(`/books/${createResponse.body.id}`).send({
      title: 'Updated Book',
      author: 'Updated Author',
      year: 2024,
      isbn: '0987654321'
    });

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message', 'Book updated successfully');
  });

  it('should delete a book', async () => {
    const createResponse = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 2023,
      isbn: '1234567890'
    });

    const response = await request(app).delete(`/books/${createResponse.body.id}`);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message', 'Book deleted successfully');
  });
});