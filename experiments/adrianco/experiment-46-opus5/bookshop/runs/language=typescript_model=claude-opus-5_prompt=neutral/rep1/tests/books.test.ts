import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';
import type { Express } from 'express';
import { createApp } from '../src/app.js';
import { BookStore } from '../src/db.js';

let store: BookStore;
let app: Express;

beforeEach(() => {
  // Each test gets its own in-memory database, so tests are fully isolated.
  store = new BookStore(':memory:');
  app = createApp(store);
});

afterEach(() => {
  store.close();
});

const dune = { title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' };
const neuromancer = {
  title: 'Neuromancer',
  author: 'William Gibson',
  year: 1984,
  isbn: '9780441569595',
};

async function seed(book: Record<string, unknown>): Promise<number> {
  const res = await request(app).post('/books').send(book).expect(201);
  return res.body.id as number;
}

describe('GET /health', () => {
  it('reports ok when the database is reachable', async () => {
    const res = await request(app).get('/health').expect(200);
    expect(res.body).toEqual({ status: 'ok', database: 'ok' });
  });

  it('reports 503 when the database is unreachable', async () => {
    // A separate store so the shared one stays open for afterEach.
    const doomed = new BookStore(':memory:');
    const doomedApp = createApp(doomed);
    doomed.close();

    const res = await request(doomedApp).get('/health').expect(503);
    expect(res.body).toEqual({ status: 'error', database: 'unavailable' });
  });
});

describe('POST /books', () => {
  it('creates a book and returns 201 with the assigned id', async () => {
    const res = await request(app).post('/books').send(dune).expect(201);

    expect(res.body).toMatchObject(dune);
    expect(res.body.id).toBeTypeOf('number');
    expect(res.headers['location']).toBe(`/books/${res.body.id}`);

    // The book is really persisted, not just echoed back.
    const fetched = await request(app).get(`/books/${res.body.id}`).expect(200);
    expect(fetched.body).toEqual(res.body);
  });

  it('defaults the optional year and isbn to null', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Untitled', author: 'Anon' })
      .expect(201);

    expect(res.body).toMatchObject({ year: null, isbn: null });
  });

  it('trims surrounding whitespace from title and author', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: '  Dune  ', author: '\tFrank Herbert\n' })
      .expect(201);

    expect(res.body).toMatchObject({ title: 'Dune', author: 'Frank Herbert' });
  });

  it('rejects a missing title with 400 and a field-level error', async () => {
    const res = await request(app)
      .post('/books')
      .send({ author: 'Frank Herbert' })
      .expect(400);

    expect(res.body.error).toBe('validation failed');
    expect(res.body.details).toContainEqual({
      field: 'title',
      message: 'title is required',
    });
  });

  it('rejects a whitespace-only author with 400', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: '   ' })
      .expect(400);

    expect(res.body.details).toContainEqual({
      field: 'author',
      message: 'author must not be empty',
    });
  });

  it('reports every invalid field at once', async () => {
    const res = await request(app)
      .post('/books')
      .send({ year: 'nineteen sixty-five', isbn: 'not-an-isbn' })
      .expect(400);

    expect(res.body.details.map((d: { field: string }) => d.field).sort()).toEqual([
      'author',
      'isbn',
      'title',
      'year',
    ]);
  });

  it('rejects a non-integer year', async () => {
    const res = await request(app)
      .post('/books')
      .send({ ...dune, year: 1965.5 })
      .expect(400);

    expect(res.body.details).toContainEqual({
      field: 'year',
      message: 'year must be an integer',
    });
  });

  it('accepts a hyphenated ISBN-10 with an X check digit', async () => {
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Frank Herbert', isbn: '0-441-01359-X' })
      .expect(201);

    expect(res.body.isbn).toBe('0-441-01359-X');
  });

  it('rejects a duplicate isbn with 409', async () => {
    await seed(dune);
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune (reprint)', author: 'Frank Herbert', isbn: dune.isbn })
      .expect(409);

    expect(res.body.error).toMatch(/already exists/);
  });

  it('rejects a malformed JSON body with 400', async () => {
    const res = await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send('{"title": ')
      .expect(400);

    expect(res.body.error).toBe('request body is not valid JSON');
  });

  it('rejects a body over the 100kb limit with 413', async () => {
    const res = await request(app)
      .post('/books')
      .set('Content-Type', 'application/json')
      .send(JSON.stringify({ title: 'x'.repeat(200_000), author: 'Anon' }))
      .expect(413);

    expect(res.body.error).toBe('request body too large');
  });
});

describe('GET /books', () => {
  it('returns an empty array when no books exist', async () => {
    const res = await request(app).get('/books').expect(200);
    expect(res.body).toEqual([]);
  });

  it('lists all books in insertion order', async () => {
    await seed(dune);
    await seed(neuromancer);

    const res = await request(app).get('/books').expect(200);
    expect(res.body.map((b: { title: string }) => b.title)).toEqual([
      'Dune',
      'Neuromancer',
    ]);
  });

  it('filters by author, case-insensitively', async () => {
    await seed(dune);
    await seed(neuromancer);
    await seed({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });

    const res = await request(app).get('/books?author=frank%20herbert').expect(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === 'Frank Herbert')).toBe(
      true,
    );
  });

  it('returns an empty array when the author filter matches nothing', async () => {
    await seed(dune);
    const res = await request(app).get('/books?author=Ursula%20K.%20Le%20Guin').expect(200);
    expect(res.body).toEqual([]);
  });

  it('treats an author filter as a literal, not a LIKE pattern', async () => {
    await seed(dune);
    const res = await request(app).get('/books?author=%25').expect(200);
    expect(res.body).toEqual([]);
  });
});

describe('GET /books/:id', () => {
  it('returns the requested book', async () => {
    const id = await seed(dune);
    const res = await request(app).get(`/books/${id}`).expect(200);
    expect(res.body).toEqual({ id, ...dune });
  });

  it('returns 404 for an unknown id', async () => {
    const res = await request(app).get('/books/9999').expect(404);
    expect(res.body.error).toBe('book 9999 not found');
  });

  it('returns 400 for a non-numeric id', async () => {
    const res = await request(app).get('/books/abc').expect(400);
    expect(res.body.error).toBe('id must be a positive integer');
  });
});

describe('PUT /books/:id', () => {
  it('replaces the book and returns the updated representation', async () => {
    const id = await seed(dune);
    const updated = {
      title: 'Dune',
      author: 'Frank Patrick Herbert',
      year: 1965,
      isbn: '9780441013593',
    };

    const res = await request(app).put(`/books/${id}`).send(updated).expect(200);
    expect(res.body).toEqual({ id, ...updated });

    const fetched = await request(app).get(`/books/${id}`).expect(200);
    expect(fetched.body).toEqual({ id, ...updated });
  });

  it('clears optional fields that are omitted from the replacement', async () => {
    const id = await seed(dune);
    const res = await request(app)
      .put(`/books/${id}`)
      .send({ title: 'Dune', author: 'Frank Herbert' })
      .expect(200);

    expect(res.body).toEqual({ id, title: 'Dune', author: 'Frank Herbert', year: null, isbn: null });
  });

  it('returns 404 for an unknown id', async () => {
    await request(app).put('/books/9999').send(dune).expect(404);
  });

  it('validates the body before touching the store', async () => {
    const id = await seed(dune);
    const res = await request(app)
      .put(`/books/${id}`)
      .send({ author: 'Frank Herbert' })
      .expect(400);

    expect(res.body.details).toContainEqual({
      field: 'title',
      message: 'title is required',
    });

    // The stored book is unchanged.
    const fetched = await request(app).get(`/books/${id}`).expect(200);
    expect(fetched.body).toEqual({ id, ...dune });
  });

  it('returns 409 when the new isbn collides with another book', async () => {
    await seed(dune);
    const otherId = await seed(neuromancer);

    await request(app)
      .put(`/books/${otherId}`)
      .send({ ...neuromancer, isbn: dune.isbn })
      .expect(409);
  });

  it('allows a book to keep its own isbn', async () => {
    const id = await seed(dune);
    const res = await request(app)
      .put(`/books/${id}`)
      .send({ ...dune, year: 1966 })
      .expect(200);

    expect(res.body.year).toBe(1966);
  });
});

describe('DELETE /books/:id', () => {
  it('removes the book and returns 204 with no body', async () => {
    const id = await seed(dune);

    const res = await request(app).delete(`/books/${id}`).expect(204);
    expect(res.text).toBe('');

    await request(app).get(`/books/${id}`).expect(404);
  });

  it('returns 404 when deleting the same book twice', async () => {
    const id = await seed(dune);
    await request(app).delete(`/books/${id}`).expect(204);
    await request(app).delete(`/books/${id}`).expect(404);
  });
});

describe('unknown routes', () => {
  it('returns a JSON 404', async () => {
    const res = await request(app).get('/nope').expect(404);
    expect(res.body).toEqual({ error: 'not found' });
  });
});
