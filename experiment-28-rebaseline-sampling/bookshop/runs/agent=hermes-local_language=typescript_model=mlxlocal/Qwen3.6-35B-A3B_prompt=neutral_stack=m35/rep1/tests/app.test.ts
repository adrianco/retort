import * as path from 'path';
import * as fs from 'fs';

// Set the database path BEFORE importing the app/database modules
const DB_PATH = path.join(__dirname, '..', 'test-books.db');
process.env.DB_PATH = DB_PATH;

import request from 'supertest';
import { app } from '../src/app';
import * as db from '../src/database';

// Clean up test database after all tests
afterAll(() => {
  db.closeDatabase();
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }
  [DB_PATH + '-wal', DB_PATH + '-shm'].forEach((f) => {
    if (fs.existsSync(f)) fs.unlinkSync(f);
  });
});

describe('Health Check', () => {
  test('GET /health returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('status', 'ok');
    expect(res.body).toHaveProperty('timestamp');
  });
});

describe('POST /books', () => {
  test('creates a book with all fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.title).toBe('The Great Gatsby');
    expect(res.body.author).toBe('F. Scott Fitzgerald');
    expect(res.body.year).toBe(1925);
    expect(res.body.isbn).toBe('978-0743273565');
  });

  test('creates a book without optional fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell' });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('1984');
    expect(res.body.author).toBe('George Orwell');
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  test('returns 400 when title is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'Test Author' });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });

  test('returns 400 when author is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Test Book' });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });
});

describe('GET /books', () => {
  test('lists all books', async () => {
    await request(app).post('/books').send({
      title: 'Book One',
      author: 'Author A',
      year: 2000,
    });
    await request(app).post('/books').send({
      title: 'Book Two',
      author: 'Author B',
      year: 2001,
    });

    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(2);
  });

  test('filters books by author', async () => {
    await request(app).post('/books').send({
      title: 'Book One',
      author: 'Author A',
      year: 2000,
    });
    await request(app).post('/books').send({
      title: 'Book Two',
      author: 'Author B',
      year: 2001,
    });
    await request(app).post('/books').send({
      title: 'Book Three',
      author: 'Author A',
      year: 2002,
    });

    const res = await request(app).get('/books').query({ author: 'Author A' });
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(2);
    res.body.forEach((book: any) => {
      expect(book.author).toBe('Author A');
    });
  });

  test('returns empty array when no books exist', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe('GET /books/:id', () => {
  test('returns a book by valid ID', async () => {
    const createRes = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 2020,
    });
    const bookId = createRes.body.id;

    const res = await request(app).get(`/books/${bookId}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Test Book');
  });

  test('returns 404 for non-existent ID', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Book not found');
  });

  test('returns 400 for invalid ID', async () => {
    const res = await request(app).get('/books/abc');
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid book ID');
  });
});

describe('PUT /books/:id', () => {
  test('updates a book with new title', async () => {
    const createRes = await request(app).post('/books').send({
      title: 'Original Title',
      author: 'Original Author',
    });
    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Updated Title' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Updated Title');
    expect(res.body.author).toBe('Original Author');
  });

  test('updates multiple fields', async () => {
    const createRes = await request(app).post('/books').send({
      title: 'Original Title',
      author: 'Original Author',
    });
    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'New Title', author: 'New Author', year: 2024 });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('New Author');
    expect(res.body.year).toBe(2024);
  });

  test('returns 404 for non-existent ID', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'Ghost' });
    expect(res.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  test('deletes a book and returns 204', async () => {
    const createRes = await request(app).post('/books').send({
      title: 'To Delete',
      author: 'Author',
    });
    const bookId = createRes.body.id;

    const res = await request(app).delete(`/books/${bookId}`);
    expect(res.status).toBe(204);

    // Verify it's gone
    const getRes = await request(app).get(`/books/${bookId}`);
    expect(getRes.status).toBe(404);
  });

  test('returns 404 for non-existent ID', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
