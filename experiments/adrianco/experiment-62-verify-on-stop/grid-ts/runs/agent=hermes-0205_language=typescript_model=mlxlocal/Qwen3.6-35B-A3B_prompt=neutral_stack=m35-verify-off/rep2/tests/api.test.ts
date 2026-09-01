import request from 'supertest';
import { app } from '../src/index';
import { getDb } from '../src/database';

const db = getDb();

describe('Book Collection API', () => {
  beforeEach(() => {
    db.prepare('DELETE FROM books').run();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('status', 'ok');
      expect(res.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book and return 201', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });

      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
    });

    it('should reject creation without title', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Some Author' });

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error', 'Title and author are required');
    });

    it('should reject creation without author', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Some Title' });

      expect(res.status).toBe(400);
      expect(res.body).toHaveProperty('error', 'Title and author are required');
    });

    it('should allow year and isbn to be omitted', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'A Title', author: 'An Author' });

      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe('GET /books', () => {
    it('should return empty array when no books exist', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(0);
    });

    it('should return all books', async () => {
      db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Book A', 'Author X', 2000, 'isbn-a');
      db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Book B', 'Author Y', 2001, 'isbn-b');

      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body.length).toBe(2);
    });

    it('should filter books by author', async () => {
      db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Book A', 'Author X', 2000, 'isbn-a');
      db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Book B', 'Author X', 2001, 'isbn-b');
      db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Book C', 'Author Y', 2002, 'isbn-c');

      const res = await request(app).get('/books').query({ author: 'Author X' });
      expect(res.status).toBe(200);
      expect(res.body.length).toBe(2);
      expect(res.body.every((b: any) => b.author === 'Author X')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/999');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error', 'Book not found');
    });

    it('should return a book by ID', async () => {
      const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Test Book', 'Test Author', 2023, '123');
      const bookId = result.lastInsertRowid as number;

      const res = await request(app).get(`/books/${bookId}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Test Book');
      expect(res.body.author).toBe('Test Author');
    });
  });

  describe('PUT /books/:id', () => {
    it('should return 404 for non-existent book', async () => {
      const res = await request(app).put('/books/999').send({ title: 'Updated', author: 'Updated' });
      expect(res.status).toBe(404);
    });

    it('should update an existing book', async () => {
      const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Old Title', 'Old Author', 2020, 'old');
      const bookId = result.lastInsertRowid as number;

      const res = await request(app)
        .put(`/books/${bookId}`)
        .send({ title: 'New Title', author: 'New Author', year: 2024, isbn: 'new' });

      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.author).toBe('New Author');
      expect(res.body.year).toBe(2024);
    });

    it('should reject update without title or author', async () => {
      const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('Title', 'Author', 2020, 'isbn');
      const bookId = result.lastInsertRowid as number;

      const res = await request(app).put(`/books/${bookId}`).send({ year: 2024 });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/999');
      expect(res.status).toBe(404);
    });

    it('should delete an existing book', async () => {
      const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run('To Delete', 'Author', 2023, 'isbn');
      const bookId = result.lastInsertRowid as number;

      const res = await request(app).delete(`/books/${bookId}`);
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('message', 'Book deleted successfully');

      // Verify it's actually gone
      const after = db.prepare('SELECT * FROM books WHERE id = ?').get(bookId);
      expect(after).toBeUndefined();
    });
  });
});
