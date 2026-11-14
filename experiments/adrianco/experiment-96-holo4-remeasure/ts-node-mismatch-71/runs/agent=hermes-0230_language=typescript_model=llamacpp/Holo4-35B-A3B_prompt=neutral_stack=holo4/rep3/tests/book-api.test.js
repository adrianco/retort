const { describe, it, before, after } = require('node:test');
const { equal, ok } = require('node:assert/strict');
const request = require('supertest');
const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'books.db');

// Clean up the database before tests
before(async () => {
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }
});

let app;
before(() => {
  app = require('../dist/app').default;
});

const API = request(app);

describe('Book API', () => {
  let createdBookId;

  describe('GET /health', () => {
    it('returns 200 with status ok', async () => {
      const res = await API.get('/health');
      equal(res.status, 200);
      equal(res.body.status, 'ok');
    });
  });

  describe('POST /books', () => {
    it('creates a book with all fields', async () => {
      const res = await API.post('/books').send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
      equal(res.status, 201);
      equal(res.body.title, 'The Great Gatsby');
      equal(res.body.author, 'F. Scott Fitzgerald');
      equal(res.body.year, 1925);
      equal(res.body.isbn, '978-0743273565');
      ok(res.body.id);
      createdBookId = res.body.id;
    });

    it('rejects missing title', async () => {
      const res = await API.post('/books').send({
        author: 'Someone',
      });
      equal(res.status, 400);
      ok(res.body.errors);
    });

    it('rejects missing author', async () => {
      const res = await API.post('/books').send({
        title: 'Some Book',
      });
      equal(res.status, 400);
      ok(res.body.errors);
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      const res = await API.get('/books');
      equal(res.status, 200);
      ok(Array.isArray(res.body));
    });

    it('filters by author', async () => {
      const res = await API.get('/books?author=F. Scott Fitzgerald');
      equal(res.status, 200);
      ok(Array.isArray(res.body));
      res.body.forEach((book) => {
        equal(book.author, 'F. Scott Fitzgerald');
      });
    });
  });

  describe('GET /books/:id', () => {
    it('gets a single book', async () => {
      const res = await API.get(`/books/${createdBookId}`);
      equal(res.status, 200);
      equal(res.body.id, createdBookId);
    });

    it('returns 404 for missing book', async () => {
      const res = await API.get('/books/9999');
      equal(res.status, 404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const res = await API.put(`/books/${createdBookId}`).send({
        title: 'The Great Gatsby (Updated)',
      });
      equal(res.status, 200);
      equal(res.body.title, 'The Great Gatsby (Updated)');
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book', async () => {
      const res = await API.delete(`/books/${createdBookId}`);
      equal(res.status, 204);
    });

    it('returns 404 for already deleted book', async () => {
      const res = await API.delete(`/books/${createdBookId}`);
      equal(res.status, 404);
    });
  });
});
