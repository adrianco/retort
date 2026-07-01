import request from 'supertest';
import { buildApp } from './app';
import Database from 'better-sqlite3';

const db = new Database(':memory:');
const app = buildApp(db);

describe('GET /health', () => {
  it('returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});

describe('POST /books', () => {
  beforeEach(() => {
    db.exec('DELETE FROM books');
  });

  it('creates a book and returns 201 with the book', async () => {
    const res = await request(app).post('/books').send({
      title: 'The Pragmatic Programmer',
      author: 'David Thomas',
      year: 1999,
      isbn: '978-0201616224',
    });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: 'The Pragmatic Programmer',
      author: 'David Thomas',
      year: 1999,
      isbn: '978-0201616224',
    });
  });

  it('returns 400 when title is missing', async () => {
    const res = await request(app).post('/books').send({ author: 'Someone' });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  it('returns 400 when author is missing', async () => {
    const res = await request(app).post('/books').send({ title: 'Some Book' });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });
});

describe('GET /books', () => {
  beforeEach(() => {
    db.exec('DELETE FROM books');
    db.exec(`INSERT INTO books (title, author, year, isbn) VALUES
      ('Clean Code', 'Robert Martin', 2008, '978-0132350884'),
      ('Refactoring', 'Martin Fowler', 1999, '978-0201485677')`);
  });

  it('returns all books', async () => {
    const res = await request(app).get('/books');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('filters by author', async () => {
    const res = await request(app).get('/books?author=Martin Fowler');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe('Martin Fowler');
  });
});

describe('GET /books/:id', () => {
  let bookId: number;

  beforeEach(() => {
    db.exec('DELETE FROM books');
    const result = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES ('SICP', 'Abelson', 1996, '978-0262510875')"
    ).run();
    bookId = Number(result.lastInsertRowid);
  });

  it('returns the book by id', async () => {
    const res = await request(app).get(`/books/${bookId}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('SICP');
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).get('/books/99999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /books/:id', () => {
  let bookId: number;

  beforeEach(() => {
    db.exec('DELETE FROM books');
    const result = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES ('Old Title', 'Old Author', 2000, '000')"
    ).run();
    bookId = Number(result.lastInsertRowid);
  });

  it('updates a book and returns it', async () => {
    const res = await request(app).put(`/books/${bookId}`).send({
      title: 'New Title',
      author: 'New Author',
    });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New Title');
    expect(res.body.author).toBe('New Author');
  });

  it('returns 400 when title is missing', async () => {
    const res = await request(app).put(`/books/${bookId}`).send({ author: 'A' });
    expect(res.status).toBe(400);
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).put('/books/99999').send({ title: 'X', author: 'Y' });
    expect(res.status).toBe(404);
  });
});

describe('DELETE /books/:id', () => {
  let bookId: number;

  beforeEach(() => {
    db.exec('DELETE FROM books');
    const result = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES ('To Delete', 'Author', 2020, '123')"
    ).run();
    bookId = Number(result.lastInsertRowid);
  });

  it('deletes a book and returns 204', async () => {
    const res = await request(app).delete(`/books/${bookId}`);
    expect(res.status).toBe(204);
    const check = await request(app).get(`/books/${bookId}`);
    expect(check.status).toBe(404);
  });

  it('returns 404 for unknown id', async () => {
    const res = await request(app).delete('/books/99999');
    expect(res.status).toBe(404);
  });
});
