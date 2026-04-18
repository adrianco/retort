import request from 'supertest';
import path from 'path';
import fs from 'fs';

// Use a temp in-memory-equivalent DB for tests
const TEST_DB = path.join(__dirname, 'test.db');
process.env.DB_PATH = TEST_DB;

import { createApp } from '../src/app';
import { closeDb } from '../src/db';

const app = createApp();

afterAll(() => {
  closeDb();
  if (fs.existsSync(TEST_DB)) {
    fs.unlinkSync(TEST_DB);
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
  it('creates a book with valid data', async () => {
    const res = await request(app).post('/books').send({
      title: 'The Pragmatic Programmer',
      author: 'David Thomas',
      year: 1999,
      isbn: '978-0135957059',
    });
    expect(res.status).toBe(201);
    expect(res.body.id).toBeDefined();
    expect(res.body.title).toBe('The Pragmatic Programmer');
    expect(res.body.author).toBe('David Thomas');
    expect(res.body.year).toBe(1999);
    expect(res.body.isbn).toBe('978-0135957059');
  });

  it('returns 400 when title is missing', async () => {
    const res = await request(app).post('/books').send({ author: 'Some Author' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/i);
  });

  it('returns 400 when author is missing', async () => {
    const res = await request(app).post('/books').send({ title: 'Some Title' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/author/i);
  });

  it('creates a book with only required fields', async () => {
    const res = await request(app).post('/books').send({
      title: 'Minimal Book',
      author: 'Author Name',
    });
    expect(res.status).toBe(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });
});

describe('GET /books', () => {
  it('returns an array of books', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it('filters by author', async () => {
    await request(app).post('/books').send({ title: 'Book A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'Book B', author: 'Bob' });

    const res = await request(app).get('/books?author=Alice');
    expect(res.status).toBe(200);
    expect(res.body.every((b: { author: string }) => b.author.includes('Alice'))).toBe(true);
  });
});

describe('GET /books/:id', () => {
  it('returns a book by id', async () => {
    const created = await request(app).post('/books').send({
      title: 'Clean Code',
      author: 'Robert Martin',
    });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Clean Code');
  });

  it('returns 404 for non-existent id', async () => {
    const res = await request(app).get('/books/999999');
    expect(res.status).toBe(404);
    expect(res.body.error).toMatch(/not found/i);
  });
});

describe('PUT /books/:id', () => {
  it('updates an existing book', async () => {
    const created = await request(app).post('/books').send({
      title: 'Old Title',
      author: 'Old Author',
      year: 2000,
    });
    const id = created.body.id;

    const res = await request(app).put(`/books/${id}`).send({ title: 'New Title', year: 2024 });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('Old Author');
    expect(res.body.year).toBe(2024);
  });

  it('returns 404 for non-existent id', async () => {
    const res = await request(app).put('/books/999999').send({ title: 'X' });
    expect(res.status).toBe(404);
  });

  it('returns 400 when setting title to empty string', async () => {
    const created = await request(app).post('/books').send({
      title: 'Valid Title',
      author: 'Author',
    });
    const res = await request(app).put(`/books/${created.body.id}`).send({ title: '  ' });
    expect(res.status).toBe(400);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes an existing book', async () => {
    const created = await request(app).post('/books').send({
      title: 'To Delete',
      author: 'Author',
    });
    const id = created.body.id;

    const delRes = await request(app).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);

    const getRes = await request(app).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });

  it('returns 404 for non-existent id', async () => {
    const res = await request(app).delete('/books/999999');
    expect(res.status).toBe(404);
  });
});
