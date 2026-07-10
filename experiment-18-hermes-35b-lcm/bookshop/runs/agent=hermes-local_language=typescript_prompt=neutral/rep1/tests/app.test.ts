import request from 'supertest';
import app from '../src/app';
import db from '../src/database';

// Clean up at the end of each test (not before seeding)
beforeEach(() => {
  const stmt = db.prepare('DELETE FROM books');
  stmt.run();
});

afterAll(() => {
  db.close();
});

describe('Health Check', () => {
  it('GET /health returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toHaveProperty('status', 'ok');
    expect(res.body).toHaveProperty('timestamp');
  });
});

describe('POST /books', () => {
  it('creates a new book with valid data', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925,
        isbn: '978-0743273565'
      });
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.title).toBe('The Great Gatsby');
    expect(res.body.author).toBe('F. Scott Fitzgerald');
    expect(res.body.year).toBe(1925);
    expect(res.body.isbn).toBe('978-0743273565');
  });

  it('rejects missing title', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        author: 'Some Author',
        year: 2020
      });
    expect(res.statusCode).toBe(400);
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors.some((e: string) => e.includes('title'))).toBe(true);
  });

  it('rejects missing author', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'Some Book',
        year: 2020
      });
    expect(res.statusCode).toBe(400);
    expect(res.body.errors.some((e: string) => e.includes('author'))).toBe(true);
  });
});

describe('GET /books', () => {
  let orwellId: number;
  let herbertId: number;

  beforeEach(async () => {
    // Seed data
    const r1 = await request(app).post('/books').send({ title: '1984', author: 'George Orwell', year: 1949, isbn: 'isbn-1' });
    const r2 = await request(app).post('/books').send({ title: 'Animal Farm', author: 'George Orwell', year: 1945, isbn: 'isbn-2' });
    const r3 = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: 'isbn-3' });
    orwellId = r1.body.id;
    herbertId = r3.body.id;
  });

  it('lists all books', async () => {
    const res = await request(app).get('/books');
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(3);
  });

  it('filters books by author', async () => {
    const res = await request(app).get('/books').query({ author: 'George Orwell' });
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(2);
    res.body.forEach((book: any) => {
      expect(book.author).toBe('George Orwell');
    });
  });

  it('returns empty array for unknown author', async () => {
    const res = await request(app).get('/books').query({ author: 'Unknown' });
    expect(res.statusCode).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe('GET /books/:id', () => {
  let createdBook: any;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'Brave New World',
      author: 'Aldous Huxley',
      year: 1932
    });
    createdBook = res.body;
  });

  it('returns a book by id', async () => {
    const res = await request(app).get(`/books/${createdBook.id}`);
    expect(res.statusCode).toBe(200);
    expect(res.body.id).toBe(createdBook.id);
    expect(res.body.title).toBe('Brave New World');
  });

  it('returns 404 for nonexistent book', async () => {
    const res = await request(app).get('/books/9999');
    expect(res.statusCode).toBe(404);
    expect(res.body.errors).toBeDefined();
  });
});

describe('PUT /books/:id', () => {
  let createdBook: any;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'Original Title',
      author: 'Original Author'
    });
    createdBook = res.body;
  });

  it('updates an existing book', async () => {
    const res = await request(app)
      .put(`/books/${createdBook.id}`)
      .send({
        title: 'Updated Title',
        author: 'Updated Author',
        year: 2024
      });
    expect(res.statusCode).toBe(200);
    expect(res.body.title).toBe('Updated Title');
    expect(res.body.author).toBe('Updated Author');
    expect(res.body.year).toBe(2024);
  });

  it('returns 404 for nonexistent book', async () => {
    const res = await request(app)
      .put('/books/9999')
      .send({ title: 'X', author: 'Y' });
    expect(res.statusCode).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  let createdBook: any;

  beforeEach(async () => {
    const res = await request(app).post('/books').send({
      title: 'To Delete',
      author: 'Someone'
    });
    createdBook = res.body;
  });

  it('deletes a book and returns 204', async () => {
    const res = await request(app).delete(`/books/${createdBook.id}`);
    expect(res.statusCode).toBe(204);

    // Verify deletion
    const getRes = await request(app).get(`/books/${createdBook.id}`);
    expect(getRes.statusCode).toBe(404);
  });

  it('returns 404 for nonexistent book', async () => {
    const res = await request(app).delete('/books/9999');
    expect(res.statusCode).toBe(404);
  });
});
