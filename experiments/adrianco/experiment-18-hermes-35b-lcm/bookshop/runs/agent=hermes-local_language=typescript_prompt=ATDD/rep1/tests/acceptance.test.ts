import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app';

function getDbPath(suiteName: string): string {
  return `/tmp/books-test-${Date.now()}-${Math.random().toString(36).slice(2, 9)}-${suiteName}.db`;
}

describe('Book API - Health Check', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('health')));
  });

  afterAll(() => {
    server.close();
  });

  it('should return 200 with status ok on GET /health', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('status', 'ok');
  });
});

describe('Book API - Create Book', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('create')));
  });

  afterAll(() => {
    server.close();
  });

  it('should create a new book with all fields and return 201', async () => {
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

  it('should create a book with minimal required fields (no year or isbn)', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Untitled', author: 'Anonymous' });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Untitled');
    expect(res.body.author).toBe('Anonymous');
    expect(res.body.year).toBe(null);
    expect(res.body.isbn).toBe(null);
  });

  it('should reject a book creation with missing title and return 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'No Title', year: 2020 });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toContain('title');
  });

  it('should reject a book creation with missing author and return 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'No Author', year: 2020 });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toContain('author');
  });

  it('should reject a book creation with both title and author missing and return 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ year: 2020 });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('should reject empty body and return 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({});

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });
});

describe('Book API - List Books', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('list')));
  });

  afterAll(() => {
    server.close();
  });

  it('should return an empty array when no books exist', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(0);
  });

  it('should list all books', async () => {
    // Create a few books
    await request(app).post('/books').send({ title: 'Book A', author: 'Author X', year: 2020 });
    await request(app).post('/books').send({ title: 'Book B', author: 'Author Y', year: 2021 });
    await request(app).post('/books').send({ title: 'Book C', author: 'Author X', year: 2022 });

    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(3);
  });

  it('should filter books by author when ?author= query param is provided', async () => {
    const res = await request(app).get('/books?author=Author%20Y');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(1);
    expect(res.body[0].author).toBe('Author Y');
  });

  it('should return empty array when no books match the author filter', async () => {
    const res = await request(app).get('/books?author=NonExistent');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(0);
  });
});

describe('Book API - Get Single Book', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('single')));
  });

  afterAll(() => {
    server.close();
  });

  it('should return a single book by ID with 200', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'To Kill a Mockingbird', author: 'Harper Lee', year: 1960, isbn: '978-0061120084' });

    const bookId = createRes.body.id;

    const res = await request(app).get(`/books/${bookId}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(bookId);
    expect(res.body.title).toBe('To Kill a Mockingbird');
    expect(res.body.author).toBe('Harper Lee');
    expect(res.body.year).toBe(1960);
    expect(res.body.isbn).toBe('978-0061120084');
  });

  it('should return 404 when book with given ID does not exist', async () => {
    const res = await request(app).get('/books/99999');
    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });
});

describe('Book API - Update Book', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('update')));
  });

  afterAll(() => {
    server.close();
  });

  it('should update an existing book and return 200', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Original Title', author: 'Original Author', year: 2000 });

    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'Updated Title', author: 'Updated Author', year: 2023, isbn: '111-1111111111' });

    expect(res.status).toBe(200);
    expect(res.body.id).toBe(bookId);
    expect(res.body.title).toBe('Updated Title');
    expect(res.body.author).toBe('Updated Author');
    expect(res.body.year).toBe(2023);
    expect(res.body.isbn).toBe('111-1111111111');
  });

  it('should partially update a book (only update some fields)', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Full Book', author: 'Full Author', year: 2010, isbn: 'original-isbn' });

    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'New Title', author: 'Full Author' });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Full Author');
    expect(res.body.year).toBe(2010);
    expect(res.body.isbn).toBe('original-isbn');
  });

  it('should return 404 when updating a non-existent book', async () => {
    const res = await request(app)
      .put('/books/99999')
      .send({ title: 'Ghost Book', author: 'Ghost Author' });

    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });

  it('should reject update with missing title and return 400', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Valid', author: 'Valid Author', year: 2020 });

    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ author: 'New Author' });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toContain('title');
  });

  it('should reject update with missing author and return 400', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Valid', author: 'Valid Author', year: 2020 });

    const bookId = createRes.body.id;

    const res = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: 'New Title' });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
    expect(res.body.error).toContain('author');
  });
});

describe('Book API - Delete Book', () => {
  let app: ReturnType<typeof createApp>['app'];
  let server: any;

  beforeAll(() => {
    ({ app, server } = createApp(getDbPath('delete')));
  });

  afterAll(() => {
    server.close();
  });

  it('should delete a book and return 200', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'To Delete', author: 'Delete Me', year: 2020 });

    const bookId = createRes.body.id;

    const res = await request(app).delete(`/books/${bookId}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(bookId);
  });

  it('should return 404 when deleting a non-existent book', async () => {
    const res = await request(app).delete('/books/99999');
    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });

  it('should no longer return a deleted book in GET /books', async () => {
    const createRes = await request(app)
      .post('/books')
      .send({ title: 'Disappear', author: 'Gone', year: 2020 });

    const bookId = createRes.body.id;

    await request(app).delete(`/books/${bookId}`);

    const listRes = await request(app).get('/books');
    const found = listRes.body.filter((b: any) => b.id === bookId);
    expect(found.length).toBe(0);
  });
});
