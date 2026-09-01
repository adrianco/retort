import request from 'supertest';
import { app, setDb, getDb } from '../src/app';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const DB_PATH = path.join(__dirname, '..', 'test-books.db');

function createTestDb(): Database.Database {
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }
  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return db;
}

let db: Database.Database;

beforeEach(() => {
  db = createTestDb();
  setDb(db);
});

afterEach(() => {
  db.close();
  if (fs.existsSync(DB_PATH)) {
    fs.unlinkSync(DB_PATH);
  }
});

describe('GET /health', () => {
  it('returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  it('creates a book with all fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '1984', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe('1984');
    expect(res.body.author).toBe('George Orwell');
    expect(res.body.year).toBe(1949);
    expect(res.body.isbn).toBe('978-0451524935');
    expect(res.body.id).toBeDefined();
  });

  it('creates a book with optional fields omitted', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert' });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Dune');
    expect(res.body.author).toBe('Frank Herbert');
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it('returns 400 when title is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'Test Author' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('title and author are required');
  });

  it('returns 400 when author is missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Test Book' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('title and author are required');
  });

  it('returns 400 when both title and author are missing', async () => {
    const res = await request(app)
      .post('/books')
      .send({});

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('title and author are required');
  });
});

describe('GET /books', () => {
  beforeEach(async () => {
    await request(app).post('/books').send({ title: '1984', author: 'George Orwell', year: 1949 });
    await request(app).post('/books').send({ title: 'Animal Farm', author: 'George Orwell', year: 1945 });
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965 });
  });

  it('returns all books', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(3);
  });

  it('filters books by author', async () => {
    const res = await request(app).get('/books?author=George Orwell');
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(2);
    expect(res.body.every((b: any) => b.author === 'George Orwell')).toBe(true);
  });

  it('returns empty array when no books match', async () => {
    const res = await request(app).get('/books?author=Unknown');
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(0);
  });
});

describe('GET /books/:id', () => {
  let bookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({ title: '1984', author: 'George Orwell', year: 1949 });
    bookId = res.body.id;
  });

  it('returns a book by id', async () => {
    const res = await request(app).get(`/books/${bookId}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('1984');
    expect(res.body.author).toBe('George Orwell');
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.status).toBe(404);
    expect(res.body.error).toBe('Book not found');
  });
});

describe('PUT /books/:id', () => {
  let bookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({ title: '1984', author: 'George Orwell', year: 1949 });
    bookId = res.body.id;
  });

  it('updates a book', async () => {
    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Nineteen Eighty-Four', author: 'George Orwell', year: 1949, isbn: '978-0451524935' });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Nineteen Eighty-Four');
    expect(res.body.isbn).toBe('978-0451524935');
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'Test', author: 'Test' });

    expect(res.status).toBe(404);
  });

  it('returns 400 when title or author missing on update', async () => {
    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Updated' });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('title and author are required');
  });
});

describe('DELETE /books/:id', () => {
  let bookId: number;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({ title: '1984', author: 'George Orwell' });
    bookId = res.body.id;
  });

  it('deletes a book', async () => {
    const res = await request(app).delete(`/books/${bookId}`);
    expect(res.status).toBe(204);

    const getRes = await request(app).get(`/books/${bookId}`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 for non-existent book', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.status).toBe(404);
  });
});
