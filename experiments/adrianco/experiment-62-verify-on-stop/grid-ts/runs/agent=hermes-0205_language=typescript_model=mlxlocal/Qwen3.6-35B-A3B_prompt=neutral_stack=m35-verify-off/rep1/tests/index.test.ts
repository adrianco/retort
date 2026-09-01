import request from 'supertest';
import { app, startServer, stopServer } from '../src/index';
import { closeDb, resetDatabase } from '../src/database';
import * as fs from 'fs';
import * as path from 'path';

const TEST_DB_PATH = path.join(__dirname, '..', 'test-books.db');

// Override the DB path before any database operations
process.env.DB_PATH = TEST_DB_PATH;

// Clean up test database files
const cleanupDbFiles = () => {
  if (fs.existsSync(TEST_DB_PATH)) {
    fs.unlinkSync(TEST_DB_PATH);
  }
  if (fs.existsSync(TEST_DB_PATH + '-wal')) {
    fs.unlinkSync(TEST_DB_PATH + '-wal');
  }
  if (fs.existsSync(TEST_DB_PATH + '-shm')) {
    fs.unlinkSync(TEST_DB_PATH + '-shm');
  }
};

beforeEach(() => {
  resetDatabase();
  cleanupDbFiles();
});

afterEach(() => {
  resetDatabase();
  cleanupDbFiles();
});

describe('Health Check', () => {
  test('GET /health should return 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.timestamp).toBeDefined();
  });
});

describe('POST /books', () => {
  test('should create a new book and return 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
    expect(res.statusCode).toBe(201);
    expect(res.body.title).toBe('The Great Gatsby');
    expect(res.body.author).toBe('F. Scott Fitzgerald');
    expect(res.body.year).toBe(1925);
    expect(res.body.isbn).toBe('978-0743273565');
    expect(res.body.id).toBeDefined();
  });

  test('should reject creation without title', async () => {
    const res = await request(app).post('/books').send({
      author: 'Test Author',
    });
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });

  test('should reject creation without author', async () => {
    const res = await request(app).post('/books').send({
      title: 'Test Book',
    });
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Validation failed');
  });

  test('should reject creation with empty title', async () => {
    const res = await request(app).post('/books').send({
      title: '',
      author: 'Test Author',
    });
    expect(res.statusCode).toBe(400);
  });

  test('should reject creation with empty author', async () => {
    const res = await request(app).post('/books').send({
      title: 'Test Book',
      author: '',
    });
    expect(res.statusCode).toBe(400);
  });

  test('should create a book with minimal fields (no year, no isbn)', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'Minimal Book',
        author: 'Anonymous',
      });
    expect(res.statusCode).toBe(201);
    expect(res.body.title).toBe('Minimal Book');
    expect(res.body.author).toBe('Anonymous');
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  test('should reject invalid year', async () => {
    const res = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 99999,
    });
    expect(res.statusCode).toBe(400);
  });
});

describe('GET /books', () => {
  beforeEach(async () => {
    // Seed some test data
    await request(app).post('/books').send({
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0743273565',
    });
    await request(app).post('/books').send({
      title: 'Tender Is the Night',
      author: 'F. Scott Fitzgerald',
      year: 1934,
      isbn: '978-0743273572',
    });
    await request(app).post('/books').send({
      title: '1984',
      author: 'George Orwell',
      year: 1949,
      isbn: '978-0451524935',
    });
  });

  test('should return all books', async () => {
    const res = await request(app).get('/books');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(3);
  });

  test('should filter books by author', async () => {
    const res = await request(app).get('/books?author=F.+Scott+Fitzgerald');
    expect(res.statusCode).toBe(200);
    expect(res.body.length).toBe(2);
    expect(res.body[0].author).toBe('F. Scott Fitzgerald');
  });

  test('should return empty array for non-matching author', async () => {
    const res = await request(app).get('/books?author=Nonexistent+Author');
    expect(res.statusCode).toBe(200);
    expect(res.body.length).toBe(0);
  });
});

describe('GET /books/:id', () => {
  let createdBookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'Test Book',
      author: 'Test Author',
      year: 2020,
      isbn: '123-456',
    });
    createdBookId = res.body.id;
  });

  test('should return a book by valid ID', async () => {
    const res = await request(app).get(`/books/${createdBookId}`);
    expect(res.statusCode).toBe(200);
    expect(res.body.title).toBe('Test Book');
    expect(res.body.author).toBe('Test Author');
  });

  test('should return 404 for non-existent book', async () => {
    const res = await request(app).get('/books/99999');
    expect(res.statusCode).toBe(404);
    expect(res.body.error).toBe('Not found');
  });

  test('should return 400 for invalid ID', async () => {
    const res = await request(app).get('/books/abc');
    expect(res.statusCode).toBe(400);
  });

  test('should return 400 for zero ID', async () => {
    const res = await request(app).get('/books/0');
    expect(res.statusCode).toBe(400);
  });

  test('should return 400 for negative ID', async () => {
    const res = await request(app).get('/books/-1');
    expect(res.statusCode).toBe(400);
  });
});

describe('PUT /books/:id', () => {
  let createdBookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'Original Title',
      author: 'Original Author',
      year: 2000,
      isbn: 'old-isbn',
    });
    createdBookId = res.body.id;
  });

  test('should update all fields of a book', async () => {
    const res = await request(app)
      .put(`/books/${createdBookId}`)
      .send({
        title: 'Updated Title',
        author: 'Updated Author',
        year: 2024,
        isbn: 'new-isbn',
      });
    expect(res.statusCode).toBe(200);
    expect(res.body.title).toBe('Updated Title');
    expect(res.body.author).toBe('Updated Author');
    expect(res.body.year).toBe(2024);
    expect(res.body.isbn).toBe('new-isbn');
  });

  test('should update only title', async () => {
    const res = await request(app)
      .put(`/books/${createdBookId}`)
      .send({ title: 'Only Title Changed' });
    expect(res.statusCode).toBe(200);
    expect(res.body.title).toBe('Only Title Changed');
    expect(res.body.author).toBe('Original Author');
    expect(res.body.year).toBe(2000);
    expect(res.body.isbn).toBe('old-isbn');
  });

  test('should return 404 for non-existent book', async () => {
    const res = await request(app)
      .put('/books/99999')
      .send({ title: 'Ghost Book' });
    expect(res.statusCode).toBe(404);
  });

  test('should reject update with empty title', async () => {
    const res = await request(app)
      .put(`/books/${createdBookId}`)
      .send({ title: '' });
    expect(res.statusCode).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  let createdBookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'To Delete',
      author: 'Author',
    });
    createdBookId = res.body.id;
  });

  test('should delete a book and return 204', async () => {
    const res = await request(app).delete(`/books/${createdBookId}`);
    expect(res.statusCode).toBe(204);
  });

  test('should remove the book from the database', async () => {
    await request(app).delete(`/books/${createdBookId}`);
    const getRes = await request(app).get(`/books/${createdBookId}`);
    expect(getRes.statusCode).toBe(404);
  });

  test('should return 404 for non-existent book', async () => {
    const res = await request(app).delete('/books/99999');
    expect(res.statusCode).toBe(404);
  });
});
