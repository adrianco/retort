import { describe, it, beforeEach } from 'mocha';
import supertest = require('supertest');
import { createApp } from '../src/server';

/**
 * Acceptance tests for Book Collection API.
 *
 * Each test starts from a clean service (fresh in-memory/empty DB).
 * Tests exercise the system through its REST API only.
 * Tests assert WHAT the system does, not HOW it does it.
 */
describe('Book Collection API', function () {
  describe('GET /health', function () {
    it('should return 200 with status ok', async () => {
      const app = createApp();
      const res = await supertest(app).get('/health');

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!res.body || res.body.status !== 'ok') {
        throw new Error(`Expected status "ok", got: ${JSON.stringify(res.body)}`);
      }
    });
  });

  describe('POST /books', function () {
    it('should create a new book and return 201 with the book object', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      if (res.status !== 201) throw new Error(`Expected 201, got ${res.status} body: ${JSON.stringify(res.body)}`);
      if (!res.body) throw new Error('Expected response body');
      if (res.body.title !== 'The Great Gatsby') throw new Error(`Expected title "The Great Gatsby", got: ${res.body.title}`);
      if (res.body.author !== 'F. Scott Fitzgerald') throw new Error(`Expected author "F. Scott Fitzgerald", got: ${res.body.author}`);
      if (res.body.year !== 1925) throw new Error(`Expected year 1925, got: ${res.body.year}`);
      if (res.body.isbn !== '978-0743273565') throw new Error(`Expected isbn "978-0743273565", got: ${res.body.isbn}`);
      if (!res.body.id) throw new Error('Expected response to include an id field');
    });

    it('should reject a book with a missing title (400)', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ author: 'Unknown Author', year: 2000, isbn: '000-0000000000' });

      if (res.status !== 400) throw new Error(`Expected 400, got ${res.status} body: ${JSON.stringify(res.body)}`);
      if (!res.body || !res.body.error) throw new Error('Expected error field in response');
    });

    it('should reject a book with a missing author (400)', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ title: 'Some Book', year: 2000, isbn: '000-0000000000' });

      if (res.status !== 400) throw new Error(`Expected 400, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });

    it('should reject a book with neither title nor author (400)', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ year: 2000 });

      if (res.status !== 400) throw new Error(`Expected 400, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });
  });

  describe('GET /books', function () {
    it('should return an empty array when no books exist', async () => {
      const app = createApp();
      const res = await supertest(app).get('/books');

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!Array.isArray(res.body)) throw new Error('Expected array response');
      if (res.body.length !== 0) throw new Error('Expected empty array');
    });

    it('should list all books after creating them', async () => {
      const app = createApp();

      // Create three books
      await supertest(app).post('/books').send({ title: 'Book One', author: 'Author A', year: 2020, isbn: '111' });
      await supertest(app).post('/books').send({ title: 'Book Two', author: 'Author B', year: 2021, isbn: '222' });
      await supertest(app).post('/books').send({ title: 'Book Three', author: 'Author A', year: 2022, isbn: '333' });

      const res = await supertest(app).get('/books');

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!Array.isArray(res.body)) throw new Error('Expected array response');
      if (res.body.length !== 3) throw new Error(`Expected 3 books, got: ${res.body.length}`);
    });

    it('should filter books by author when ?author= query param is provided', async () => {
      const app = createApp();

      await supertest(app).post('/books').send({ title: 'Book by A', author: 'Author A', year: 2020, isbn: '111' });
      await supertest(app).post('/books').send({ title: 'Book by B', author: 'Author B', year: 2021, isbn: '222' });
      await supertest(app).post('/books').send({ title: 'Another by A', author: 'Author A', year: 2022, isbn: '333' });

      const res = await supertest(app).get('/books?author=Author%20A');

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!Array.isArray(res.body)) throw new Error('Expected array response');
      if (res.body.length !== 2) throw new Error(`Expected 2 books for Author A, got: ${res.body.length}`);
      for (const book of res.body) {
        if (book.author !== 'Author A') throw new Error(`Expected all books to be by Author A, got: ${book.author}`);
      }
    });

    it('should return empty array when filtering by unknown author', async () => {
      const app = createApp();

      await supertest(app).post('/books').send({ title: 'Book by A', author: 'Author A', year: 2020, isbn: '111' });

      const res = await supertest(app).get('/books?author=Nonexistent%20Author');

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status}`);
      if (!Array.isArray(res.body)) throw new Error('Expected array response');
      if (res.body.length !== 0) throw new Error(`Expected 0 books, got: ${res.body.length}`);
    });
  });

  describe('GET /books/:id', function () {
    it('should return a single book by its ID', async () => {
      const app = createApp();

      const createRes = await supertest(app)
        .post('/books')
        .send({ title: 'Unique Book', author: 'Unique Author', year: 2019, isbn: '999' });

      if (createRes.status !== 201) throw new Error(`Create failed: ${createRes.status} ${JSON.stringify(createRes.body)}`);
      const bookId = createRes.body.id;

      const res = await supertest(app).get(`/books/${bookId}`);

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status} body: ${JSON.stringify(res.body)}`);
      if (!res.body) throw new Error('Expected response body');
      if (res.body.id !== bookId) throw new Error(`Expected id ${bookId}, got: ${res.body.id}`);
      if (res.body.title !== 'Unique Book') throw new Error(`Expected title "Unique Book", got: ${res.body.title}`);
    });

    it('should return 404 when book does not exist', async () => {
      const app = createApp();
      const res = await supertest(app).get('/books/999999');

      if (res.status !== 404) throw new Error(`Expected 404, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });
  });

  describe('PUT /books/:id', function () {
    it('should update an existing book and return the updated book', async () => {
      const app = createApp();

      const createRes = await supertest(app)
        .post('/books')
        .send({ title: 'Original Title', author: 'Original Author', year: 2000, isbn: '000' });

      const bookId = createRes.body.id;

      const res = await supertest(app)
        .put(`/books/${bookId}`)
        .send({ title: 'Updated Title', author: 'Updated Author', year: 2023, isbn: '888' });

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status} body: ${JSON.stringify(res.body)}`);
      if (res.body.id !== bookId) throw new Error(`Expected id ${bookId}, got: ${res.body.id}`);
      if (res.body.title !== 'Updated Title') throw new Error(`Expected title "Updated Title", got: ${res.body.title}`);
      if (res.body.author !== 'Updated Author') throw new Error(`Expected author "Updated Author", got: ${res.body.author}`);
      if (res.body.year !== 2023) throw new Error(`Expected year 2023, got: ${res.body.year}`);
    });

    it('should return 404 when updating a non-existent book', async () => {
      const app = createApp();
      const res = await supertest(app)
        .put('/books/999999')
        .send({ title: 'No One Here', author: 'Nobody', year: 2023 });

      if (res.status !== 404) throw new Error(`Expected 404, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });

    it('should reject update with missing title (400)', async () => {
      const app = createApp();

      const createRes = await supertest(app)
        .post('/books')
        .send({ title: 'Original Title', author: 'Original Author', year: 2000, isbn: '000' });

      const bookId = createRes.body.id;

      const res = await supertest(app)
        .put(`/books/${bookId}`)
        .send({ author: 'No Title Author', year: 2023 });

      if (res.status !== 400) throw new Error(`Expected 400, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });
  });

  describe('DELETE /books/:id', function () {
    it('should delete a book and return 200 with the deleted book', async () => {
      const app = createApp();

      const createRes = await supertest(app)
        .post('/books')
        .send({ title: 'To Delete', author: 'Delete Me', year: 2010, isbn: '123' });

      const bookId = createRes.body.id;

      const res = await supertest(app).delete(`/books/${bookId}`);

      if (res.status !== 200) throw new Error(`Expected 200, got ${res.status} body: ${JSON.stringify(res.body)}`);
      if (!res.body) throw new Error('Expected response body');
      if (res.body.id !== bookId) throw new Error(`Expected id ${bookId}, got: ${res.body.id}`);
      if (res.body.title !== 'To Delete') throw new Error(`Expected title "To Delete", got: ${res.body.title}`);

      // Verify the book is gone
      const getRes = await supertest(app).get(`/books/${bookId}`);
      if (getRes.status !== 404) throw new Error(`Expected 404 after delete, got ${getRes.status}`);
    });

    it('should return 404 when deleting a non-existent book', async () => {
      const app = createApp();
      const res = await supertest(app).delete('/books/999999');

      if (res.status !== 404) throw new Error(`Expected 404, got ${res.status} body: ${JSON.stringify(res.body)}`);
    });

    it('should remove the book from the list after deletion', async () => {
      const app = createApp();

      const createRes = await supertest(app)
        .post('/books')
        .send({ title: 'Gone Book', author: 'Gone Author', year: 2015, isbn: '456' });

      const bookId = createRes.body.id;

      await supertest(app).delete(`/books/${bookId}`);

      const listRes = await supertest(app).get('/books');
      if (listRes.status !== 200) throw new Error(`Expected 200, got ${listRes.status}`);
      if (listRes.body.length !== 0) throw new Error(`Expected 0 books after delete, got: ${listRes.body.length}`);
    });
  });
});
