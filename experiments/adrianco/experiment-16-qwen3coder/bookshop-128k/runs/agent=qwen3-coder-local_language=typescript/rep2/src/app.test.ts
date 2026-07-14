import request from 'supertest';
import { app } from './app';
import { describe, it } from 'mocha';
import { expect } from 'chai';

describe('Book Collection API', () => {
  // We'll test using the in-memory database approach
  // Since we can't easily mock the database in this simple implementation,
  // we'll focus on integration testing with a clean database

  describe('Health Check', () => {
    it('should return health status', async () => {
      const res = await request(app).get('/health');
      expect(res.status).to.equal(200);
      expect(res.body).to.have.property('status', 'OK');
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

      const res = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);

      expect(res.body).to.have.property('title', 'The Great Gatsby');
      expect(res.body).to.have.property('author', 'F. Scott Fitzgerald');
      expect(res.body).to.have.property('year', 1925);
      expect(res.body).to.have.property('isbn', '978-0-7432-7356-5');
      expect(res.body).to.have.property('id');
    });

    it('should return error for missing required fields', async () => {
      const bookData = {
        title: 'The Great Gatsby'
        // Missing author
      };

      const res = await request(app)
        .post('/books')
        .send(bookData)
        .expect(400);

      expect(res.body).to.have.property('error');
    });
  });

  describe('GET /books', () => {
    it('should return all books', async () => {
      const res = await request(app).get('/books').expect(200);
      expect(res.body).to.be.an('array');
    });

    it('should filter books by author', async () => {
      const res = await request(app)
        .get('/books')
        .query({ author: 'George Orwell' })
        .expect(200);
      
      expect(res.body).to.be.an('array');
    });
  });

  describe('GET /books/:id', () => {
    it('should return a book by ID', async () => {
      // First create a book to get an ID
      const bookData = {
        title: '1984',
        author: 'George Orwell',
        year: 1948,
        isbn: '978-0-452-28423-4'
      };

      const createRes = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);
      
      const bookId = createRes.body.id;

      const res = await request(app).get(`/books/${bookId}`).expect(200);
      expect(res.body).to.have.property('title', '1984');
      expect(res.body).to.have.property('author', 'George Orwell');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/999').expect(404);
      expect(res.body).to.have.property('error');
    });

    it('should return 400 for invalid ID', async () => {
      const res = await request(app).get('/books/invalid').expect(400);
      expect(res.body).to.have.property('error');
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      // First create a book
      const bookData = {
        title: '1984',
        author: 'George Orwell',
        year: 1948,
        isbn: '978-0-452-28423-4'
      };

      const createRes = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);
      
      const bookId = createRes.body.id;
      
      const updateData = {
        title: '1984 - Updated',
        author: 'George Orwell',
        year: 1949,
        isbn: '978-0-452-28423-5'
      };

      const res = await request(app)
        .put(`/books/${bookId}`)
        .send(updateData)
        .expect(200);

      expect(res.body).to.have.property('title', '1984 - Updated');
      expect(res.body).to.have.property('year', 1949);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book', async () => {
      // First create a book to get an ID
      const bookData = {
        title: '1984',
        author: 'George Orwell',
        year: 1948,
        isbn: '978-0-452-28423-4'
      };

      const createRes = await request(app)
        .post('/books')
        .send(bookData)
        .expect(201);
      
      const bookId = createRes.body.id;

      const res = await request(app).delete(`/books/${bookId}`).expect(200);
      expect(res.body).to.have.property('message');

      // Verify book is deleted
      const getRes = await request(app).get(`/books/${bookId}`).expect(404);
      expect(getRes.body).to.have.property('error');
    });
  });
});