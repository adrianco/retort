import request from 'supertest';
import { app } from '../src/app';
import { closeDb } from '../src/db';
import fs from 'fs';
import path from 'path';

const DB_FILE = path.join(process.cwd(), 'books.db');

afterAll(() => {
  closeDb();
  if (fs.existsSync(DB_FILE)) fs.unlinkSync(DB_FILE);
});

beforeEach(() => {
  // Clean up database file before each test
  if (fs.existsSync(DB_FILE)) fs.unlinkSync(DB_FILE);
  closeDb();
});

describe('Book API', () => {
  beforeEach(() => {
    // Reset the database before each test
    closeDb();
  });

  describe('GET /health', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('should create a new book and return 201', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565',
      });
      expect(res.body.id).toBeDefined();
    });

    it('should return 400 if title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Test', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Validation failed');
    });

    it('should return 400 if author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Test', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Validation failed');
    });

    it('should return 409 if ISBN already exists', async () => {
      await request(app)
        .post('/books')
        .send({ title: 'Book 1', author: 'Author 1', year: 2020, isbn: 'same-isbn' });
      const res = await request(app)
        .post('/books')
        .send({ title: 'Book 2', author: 'Author 2', year: 2021, isbn: 'same-isbn' });
      expect(res.status).toBe(409);
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      await request(app)
        .post('/books')
        .send({ title: 'Book A', author: 'Author A', year: 2020, isbn: 'isbn-a' });
      await request(app)
        .post('/books')
        .send({ title: 'Book B', author: 'Author A', year: 2021, isbn: 'isbn-b' });
      await request(app)
        .post('/books')
        .send({ title: 'Book C', author: 'Author B', year: 2022, isbn: 'isbn-c' });
    });

    it('should return all books', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it('should filter books by author', async () => {
      const res = await request(app).get('/books?author=Author A');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: any) => b.author === 'Author A')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Test Book', author: 'Test Author', year: 2023, isbn: 'isbn-test' });
      createdBook = res.body;
    });

    it('should return a book by id', async () => {
      const res = await request(app).get(`/books/${createdBook.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Test Book');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).get('/books/99999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Old Title', author: 'Old Author', year: 2020, isbn: 'isbn-update' });
      createdBook = res.body;
    });

    it('should update a book', async () => {
      const res = await request(app)
        .put(`/books/${createdBook.id}`)
        .send({ title: 'New Title', year: 2021 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('New Title');
      expect(res.body.year).toBe(2021);
      expect(res.body.author).toBe('Old Author');
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app)
        .put('/books/99999')
        .send({ title: 'Nope' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Delete Me', author: 'Author', year: 2020, isbn: 'isbn-delete' });
      createdBook = res.body;
    });

    it('should delete a book and return 204', async () => {
      const res = await request(app).delete(`/books/${createdBook.id}`);
      expect(res.status).toBe(204);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(app).delete('/books/99999');
      expect(res.status).toBe(404);
    });

    it('should not return the book after deletion', async () => {
      await request(app).delete(`/books/${createdBook.id}`);
      const res = await request(app).get(`/books/${createdBook.id}`);
      expect(res.status).toBe(404);
    });
  });
});
