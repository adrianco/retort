import request from 'supertest';
import app from './src/index';

describe('Book API', () => {
  it('should return health status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'OK');
  });

  it('should create a new book', async () => {
    const newBook = {
      title: 'Test Book',
      author: 'Test Author',
      year: 2023,
      isbn: '1234567890'
    };

    const response = await request(app).post('/books').send(newBook);
    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('title', newBook.title);
    expect(response.body).toHaveProperty('author', newBook.author);
  });
});