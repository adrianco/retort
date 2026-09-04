const request = require('supertest');
const { app, initDB } = require('./src/index.js');

describe('Book API - Integration Tests', () => {
  beforeAll(async () => {
    await initDB();
  });

  test('Health check endpoint should return OK', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'OK');
  });

  test('POST /books should create a new book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(newBook)
      .expect(201);

    expect(response.body).toHaveProperty('title', 'The Great Gatsby');
    expect(response.body).toHaveProperty('author', 'F. Scott Fitzgerald');
    expect(response.body).toHaveProperty('year', 1925);
    expect(response.body).toHaveProperty('isbn', '978-0-7432-7356-5');
  });

  test('POST /books should reject missing title or author', async () => {
    const bookWithoutTitle = {
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(bookWithoutTitle)
      .expect(400);

    expect(response.body).toHaveProperty('error');

    const bookWithoutAuthor = {
      title: 'The Great Gatsby',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response2 = await request(app)
      .post('/books')
      .send(bookWithoutAuthor)
      .expect(400);

    expect(response2.body).toHaveProperty('error');
  });
});