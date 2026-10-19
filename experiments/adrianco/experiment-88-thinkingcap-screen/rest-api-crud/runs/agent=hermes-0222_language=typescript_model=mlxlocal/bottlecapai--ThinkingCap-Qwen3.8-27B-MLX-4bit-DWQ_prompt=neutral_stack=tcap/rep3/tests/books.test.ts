import { beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app.js';
import { openDb, type Book } from '../src/db.js';

let app: Express;

beforeEach(() => {
  // Fresh in-memory database per test
  app = createApp(openDb(':memory:'));
});

describe('GET /', () => {
  it('returns service info', async () => {
    const res = await request(app).get('/').expect(200);
    expect(res.body.name).toBe('book-api');
    expect(res.body.status).toBe('ok');
    expect(res.body.endpoints).toContain('POST /books');
  });
});

describe('GET /health', () => {
  it('returns 200 with status ok', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(typeof res.body.uptime).toBe('number');
  });
});

describe('POST /books', () => {
  it('creates a book with all fields and returns 201', async () => {
    const res = await request(app)
      .post('/books')
      .send({
        title: 'The Hobbit',
        author: 'J.R.R. Tolkien',
        year: 1937,
        isbn: '978-0-261-10235-9',
      })
      .expect(201);
    expect(res.body).toMatchObject({
      title: 'The Hobbit',
      author: 'J.R.R. Tolkien',
      year: 1937,
      isbn: '978-0-261-10235-9',
    });
    expect(res.body.id).toBeGreaterThan(0);
  });

  it('creates a book with only the required fields', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert' })
      .expect(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it('rejects a missing title with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'Someone' })
      .expect(400);
    expect(res.body.error).toMatch(/title/);
  });

  it('rejects a missing author with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Something' })
      .expect(400);
    expect(res.body.error).toMatch(/author/);
  });

  it('rejects an empty-string title with 400', async () => {
    await request(app)
      .post('/books')
      .send({ title: '   ', author: 'X' })
      .expect(400);
  });

  it('rejects an invalid year with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A', year: 'not-a-number' })
      .expect(400);
    expect(res.body.error).toMatch(/year/);
  });

  it('rejects a year out of range with 400', async () => {
    await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A', year: 999 })
      .expect(400);
  });

  it('rejects an invalid isbn with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A', isbn: '12345' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/isbn/);
  });

  it('rejects a malformed JSON body with 400', async () => {
    await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send('{"title": broken')
      .expect(400);
  });

  it('rejects a non-object body with 400', async () => {
    await request(app).post('/books').send('just a string').expect(400);
  });
});

describe('GET /books', () => {
  it('returns an empty list when no books exist', async () => {
    const res = await request(app).get('/books').expect(200);
    expect(res.body).toEqual([]);
  });

  it('lists all created books', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'One' });
    await request(app).post('/books').send({ title: 'B', author: 'Two' });
    const res = await request(app).get('/books').expect(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.map((b: Book) => b.title)).toEqual(['A', 'B']);
  });

  it('filters by author (?author=)', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Tolkien' });
    await request(app).post('/books').send({ title: 'B', author: 'Le Guin' });
    const res = await request(app).get('/books?author=Tolkien').expect(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].title).toBe('A');
  });

  it('author filter is case-insensitive', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Tolkien' });
    const res = await request(app).get('/books?author=tolkien').expect(200);
    expect(res.body).toHaveLength(1);
  });

  it('returns an empty list when the author filter matches nothing', async () => {
    await request(app).post('/books').send({ title: 'A', author: 'Tolkien' });
    const res = await request(app).get('/books?author=Nobody').expect(200);
    expect(res.body).toEqual([]);
  });
});

describe('GET /books/:id', () => {
  it('returns the book by id', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Neuromancer', author: 'William Gibson', year: 1984 });
    const res = await request(app).get(`/books/${created.body.id}`).expect(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: 'Neuromancer',
      author: 'William Gibson',
      year: 1984,
    });
  });

  it('returns 404 for a non-existent id', async () => {
    const res = await request(app).get('/books/99999').expect(404);
    expect(res.body.error).toMatch(/not found/);
  });

  it('returns 400 for a non-numeric id', async () => {
    await request(app).get('/books/abc').expect(400);
  });
});

describe('PUT /books/:id', () => {
  it('updates provided fields and preserves the rest', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'Old Title', author: 'A', year: 1990, isbn: '978-0-14-044913-4' });
    const id = created.body.id;
    const res = await request(app)
      .put(`/books/${id}`)
      .send({ title: 'New Title', year: 1995 })
      .expect(200);
    expect(res.body).toMatchObject({
      id,
      title: 'New Title',
      author: 'A',
      year: 1995,
      isbn: '978-0-14-044913-4',
    });
  });

  it('clears optional fields when explicitly set to null', async () => {
    const created = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A', year: 1990, isbn: '978-0-14-044913-4' });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ year: null, isbn: null })
      .expect(200);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it('returns 404 for a non-existent id', async () => {
    await request(app)
      .put('/books/99999')
      .send({ title: 'X' })
      .expect(404);
  });

  it('rejects an empty title with 400', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: '  ' })
      .expect(400);
  });

  it('rejects an empty body with 400', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const res = await request(app).put(`/books/${created.body.id}`).send({}).expect(400);
    expect(res.body.error).toMatch(/at least one/);
  });
});

describe('DELETE /books/:id', () => {
  it('deletes a book (204) and it is gone afterwards', async () => {
    const created = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const id = created.body.id;
    await request(app).delete(`/books/${id}`).expect(204);
    await request(app).get(`/books/${id}`).expect(404);
    const list = await request(app).get('/books').expect(200);
    expect(list.body).toEqual([]);
  });

  it('returns 404 for a non-existent id', async () => {
    await request(app).delete('/books/99999').expect(404);
  });
});

describe('unknown routes', () => {
  it('returns 404 JSON for unknown paths', async () => {
    const res = await request(app).get('/nope').expect(404);
    expect(res.body.error).toBe('Not found');
  });
});
