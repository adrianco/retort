import { app } from './src/server';
import request from 'supertest';
import { expect } from 'chai';

describe('Book API', () => {
  it('should return health status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('status', 'OK');
  });

  it('should return empty book list initially', async () => {
    const response = await request(app).get('/books');
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('books');
    expect(response.body.books).to.be.an('array');
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
    
    expect(response.status).to.equal(201);
    expect(response.body).to.have.property('book');
    expect(response.body.book).to.have.property('title', 'Test Book');
  });

  it('should get all books', async () => {
    const response = await request(app).get('/books');
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('books');
    expect(response.body.books).to.be.an('array');
  });

  it('should get a single book by ID', async () => {
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'Another Test Book',
        author: 'Another Author',
        year: 2023,
        isbn: '0987654321'
      });

    const bookId = createResponse.body.book.id;
    const response = await request(app).get(`/books/${bookId}`);
    
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('book');
    expect(response.body.book).to.have.property('title', 'Another Test Book');
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

    const bookId = createResponse.body.book.id;
    const response = await request(app)
      .put(`/books/${bookId}`)
      .send({
        title: 'Updated Test Book',
        author: 'Updated Author',
        year: 2024,
        isbn: '0987654321'
      });
    
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('book');
    expect(response.body.book).to.have.property('title', 'Updated Test Book');
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

    const bookId = createResponse.body.book.id;
    const response = await request(app).delete(`/books/${bookId}`);
    
    expect(response.status).to.equal(200);
    expect(response.body).to.have.property('message', 'Book deleted successfully');
  });
});