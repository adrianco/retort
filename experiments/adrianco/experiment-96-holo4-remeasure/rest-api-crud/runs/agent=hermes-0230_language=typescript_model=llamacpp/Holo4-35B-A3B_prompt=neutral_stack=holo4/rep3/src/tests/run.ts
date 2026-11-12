import { describe, it, before, after } from 'node:test';
import { strict as assert } from 'node:assert';
import { app } from '../index';
import { db, init, save } from '../database';
import supertest from 'supertest';

const request = supertest(app);

describe('Book API', () => {
  before(async () => {
    await init();
    // Clean up any existing data
    db!.run('DELETE FROM books');
    save();
  });

  after(() => {
    db!.close();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request.get('/health');
      assert.strictEqual(res.status, 200);
      assert.deepStrictEqual(res.body, { status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a book and return 201', async () => {
      const res = await request
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      assert.strictEqual(res.status, 201);
      assert.strictEqual(res.body.title, 'The Great Gatsby');
      assert.strictEqual(res.body.author, 'F. Scott Fitzgerald');
      assert.strictEqual(res.body.year, 1925);
      assert.strictEqual(res.body.isbn, '978-0743273565');
      assert.ok(res.body.id);
    });

    it('should reject missing title', async () => {
      const res = await request
        .post('/books')
        .send({ author: 'Test', year: 2020, isbn: '111' });
      assert.strictEqual(res.status, 400);
    });

    it('should reject missing author', async () => {
      const res = await request
        .post('/books')
        .send({ title: 'Test', year: 2020, isbn: '111' });
      assert.strictEqual(res.status, 400);
    });

    it('should reject duplicate isbn', async () => {
      const res = await request
        .post('/books')
        .send({ title: 'Duplicate', author: 'Author', year: 2020, isbn: '978-0743273565' });
      assert.strictEqual(res.status, 409);
    });
  });

  describe('GET /books', () => {
    it('should list all books', async () => {
      const res = await request.get('/books');
      assert.strictEqual(res.status, 200);
      assert.ok(Array.isArray(res.body));
      assert.ok(res.body.length > 0);
    });

    it('should filter by author', async () => {
      const res = await request.get('/books?author=F. Scott Fitzgerald');
      assert.strictEqual(res.status, 200);
      assert.strictEqual(res.body.length, 1);
      assert.strictEqual(res.body[0].author, 'F. Scott Fitzgerald');
    });
  });

  describe('GET /books/:id', () => {
    it('should get a single book', async () => {
      // Create a fresh book for this test
      const createRes = await request
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2020, isbn: '1234567890' });
      assert.strictEqual(createRes.status, 201);
      const id = createRes.body.id;
      
      const res = await request.get(`/books/${id}`);
      assert.strictEqual(res.status, 200);
      assert.strictEqual(res.body.id, id);
    });

    it('should return 404 for missing book', async () => {
      const res = await request.get('/books/9999');
      assert.strictEqual(res.status, 404);
    });
  });

  describe('PUT /books/:id', () => {
    it('should update a book', async () => {
      // Create a fresh book for this test
      const createRes = await request
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2020, isbn: '0987654321' });
      assert.strictEqual(createRes.status, 201);
      const id = createRes.body.id;
      
      const res = await request
        .put(`/books/${id}`)
        .send({ title: 'Test Book (Updated)' });
      assert.strictEqual(res.status, 200);
      assert.strictEqual(res.body.title, 'Test Book (Updated)');
    });

    it('should return 404 for missing book', async () => {
      const res = await request.put('/books/9999').send({ title: 'X' });
      assert.strictEqual(res.status, 404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should delete a book and return 204', async () => {
      // Create a fresh book for this test
      const createRes = await request
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2020, isbn: '1112223334' });
      assert.strictEqual(createRes.status, 201);
      const id = createRes.body.id;
      
      const res = await request.delete(`/books/${id}`);
      assert.strictEqual(res.status, 204);
    });

    it('should return 404 for missing book', async () => {
      const res = await request.delete('/books/9999');
      assert.strictEqual(res.status, 404);
    });
  });
});
