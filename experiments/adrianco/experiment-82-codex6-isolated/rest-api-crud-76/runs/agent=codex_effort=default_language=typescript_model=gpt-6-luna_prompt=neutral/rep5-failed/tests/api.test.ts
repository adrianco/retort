import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import Database from 'better-sqlite3';
import request from 'supertest';
import { createApp } from '../src/app.js';

describe('book collection API', () => {
  let db: Database.Database;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    db = new Database(':memory:');
    db.exec('CREATE TABLE books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)');
    app = createApp(db);
  });
  afterEach(() => db.close());

  it('reports healthy status', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok' });
  });

  it('creates and retrieves a book', async () => {
    const created = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' });
    expect(created.status).toBe(201);
    expect(created.body.id).toBe(1);
    const fetched = await request(app).get('/books/1');
    expect(fetched.status).toBe(200);
    expect(fetched.body.title).toBe('Dune');
  });

  it('validates required fields and filters by author', async () => {
    expect((await request(app).post('/books').send({ title: 'Untitled' })).status).toBe(400);
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    await request(app).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });
    const response = await request(app).get('/books?author=Frank%20Herbert');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].title).toBe('Dune');
  });

  it('updates and deletes a book', async () => {
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    const updated = await request(app).put('/books/1').send({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Dune Messiah');
    expect((await request(app).delete('/books/1')).status).toBe(204);
    expect((await request(app).get('/books/1')).status).toBe(404);
  });
});
