import request from 'supertest';
import { createApp } from '../src/app';
import { createDatabase, closeDatabase } from '../src/database';

describe('Book API', () => {
  let dbStatements: any;
  let testApp: any;

  const TEST_BOOK = {
    title: 'The Great Gatsby',
    author: 'F. Scott Fitzgerald',
    year: 1925,
    isbn: '978-0743273565',
  };

  const ANOTHER_BOOK = {
    title: '1984',
    author: 'George Orwell',
    year: 1949,
    isbn: '978-0451524935',
  };

  beforeEach(() => {
    dbStatements = createDatabase(':memory:');
    testApp = createApp(dbStatements);
  });

  afterEach(() => {
    closeDatabase(dbStatements);
  });

  describe('Health Check', () => {
    it('should return 200 with status ok', async () => {
      const res = await request(testApp).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('status', 'ok');
      expect(res.body).toHaveProperty('timestamp');
    });
  });

  describe('POST /books', () => {
    it('should create a new book and return 201', async () => {
      const res = await request(testApp).post('/books').send(TEST_BOOK);
      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe(TEST_BOOK.title);
      expect(res.body.author).toBe(TEST_BOOK.author);
      expect(res.body.year).toBe(TEST_BOOK.year);
      expect(res.body.isbn).toBe(TEST_BOOK.isbn);
    });

    it('should return 400 when title is missing', async () => {
      const { title, ...withoutTitle } = TEST_BOOK;
      const res = await request(testApp).post('/books').send(withoutTitle);
      expect(res.status).toBe(400);
      expect(res.body.errors).toContain('Title is required');
    });

    it('should return 400 when author is missing', async () => {
      const { author, ...withoutAuthor } = TEST_BOOK;
      const res = await request(testApp).post('/books').send(withoutAuthor);
      expect(res.status).toBe(400);
      expect(res.body.errors).toContain('Author is required');
    });

    it('should return 409 when isbn is duplicate', async () => {
      await request(testApp).post('/books').send(TEST_BOOK);
      const res = await request(testApp).post('/books').send(TEST_BOOK);
      expect(res.status).toBe(409);
    });

    it('should create a book without year and isbn', async () => {
      const partial = { title: 'No Year Book', author: 'Some Author' };
      const res = await request(testApp).post('/books').send(partial);
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      // Recreate db for this sub-suite since we seed it
      dbStatements = createDatabase(':memory:');
      testApp = createApp(dbStatements);
      await request(testApp).post('/books').send(TEST_BOOK);
      await request(testApp).post('/books').send(ANOTHER_BOOK);
      await request(testApp).post('/books').send({
        title: 'Animal Farm',
        author: 'George Orwell',
        year: 1945,
        isbn: '978-0451526342',
      });
    });

    it('should return all books', async () => {
      const res = await request(testApp).get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(3);
    });

    it('should filter books by author', async () => {
      const res = await request(testApp).get('/books').query({ author: 'George Orwell' });
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBe(2);
      expect(res.body.every((b: any) => b.author === 'George Orwell')).toBe(true);
    });

    it('should return empty array when no books match author', async () => {
      const res = await request(testApp).get('/books').query({ author: 'Nonexistent Author' });
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });
  });

  describe('GET /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      dbStatements = createDatabase(':memory:');
      testApp = createApp(dbStatements);
      const res = await request(testApp).post('/books').send(TEST_BOOK);
      createdBook = res.body;
    });

    it('should return a book by id', async () => {
      const res = await request(testApp).get(`/books/${createdBook.id}`);
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(createdBook.id);
      expect(res.body.title).toBe(TEST_BOOK.title);
    });

    it('should return 404 for non-existent book', async () => {
      const res = await request(testApp).get('/books/00000000-0000-0000-0000-000000000000');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('error');
    });
  });

  describe('PUT /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      dbStatements = createDatabase(':memory:');
      testApp = createApp(dbStatements);
      const res = await request(testApp).post('/books').send(TEST_BOOK);
      createdBook = res.body;
    });

    it('should update an existing book', async () => {
      const update = { title: 'Updated Title', author: 'Updated Author' };
      const res = await request(testApp).put(`/books/${createdBook.id}`).send(update);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Updated Title');
      expect(res.body.author).toBe('Updated Author');
      expect(res.body.year).toBe(1925);
    });

    it('should return 404 when updating non-existent book', async () => {
      const res = await request(testApp).put('/books/00000000-0000-0000-0000-000000000000').send({ title: 'X' });
      expect(res.status).toBe(404);
    });

    it('should return 400 when updating with invalid data', async () => {
      const res = await request(testApp).put(`/books/${createdBook.id}`).send({ author: '' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    let createdBook: any;

    beforeEach(async () => {
      dbStatements = createDatabase(':memory:');
      testApp = createApp(dbStatements);
      const res = await request(testApp).post('/books').send(TEST_BOOK);
      createdBook = res.body;
    });

    it('should delete a book and return 200', async () => {
      const res = await request(testApp).delete(`/books/${createdBook.id}`);
      expect(res.status).toBe(200);
      expect(res.body.message).toBe('Book deleted successfully');
    });

    it('should return 404 when deleting non-existent book', async () => {
      const res = await request(testApp).delete('/books/00000000-0000-0000-0000-000000000000');
      expect(res.status).toBe(404);
    });

    it('should remove the book from the database after deletion', async () => {
      await request(testApp).delete(`/books/${createdBook.id}`);
      const res = await request(testApp).get('/books');
      expect(res.status).toBe(200);
      expect(res.body.length).toBe(0);
    });
  });
});
