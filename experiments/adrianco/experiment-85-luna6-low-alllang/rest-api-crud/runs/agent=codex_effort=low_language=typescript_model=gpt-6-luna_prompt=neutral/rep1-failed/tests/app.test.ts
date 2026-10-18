import Database from 'better-sqlite3';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';

describe('book collection API', () => {
  let database: Database.Database;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    database = new Database(':memory:');
    app = createApp(database);
  });

  afterEach(() => database.close());

  it('reports health and creates a book', async () => {
    expect((await request(app).get('/health')).status).toBe(200);
    const response = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441172719' });
    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({ id: 1, title: 'Dune', author: 'Frank Herbert', year: 1965 });
  });

  it('requires title and author', async () => {
    const response = await request(app).post('/books').send({ title: 'Dune' });
    expect(response.status).toBe(400);
    expect(response.body.error).toBe('author is required');
  });

  it('lists books with a case-insensitive author filter', async () => {
    await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    await request(app).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });
    const response = await request(app).get('/books?author=frank%20herbert');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].title).toBe('Dune');
  });

  it('gets, updates, and deletes a book', async () => {
    const created = await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    const id = created.body.id;
    expect((await request(app).get(`/books/${id}`)).status).toBe(200);
    const updated = await request(app).put(`/books/${id}`).send({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Dune Messiah');
    expect((await request(app).delete(`/books/${id}`)).status).toBe(204);
    expect((await request(app).get(`/books/${id}`)).status).toBe(404);
  });
});
