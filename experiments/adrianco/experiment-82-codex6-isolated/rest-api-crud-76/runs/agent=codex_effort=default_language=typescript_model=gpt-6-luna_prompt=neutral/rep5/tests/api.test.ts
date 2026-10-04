import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app.js';
import { createDatabase } from '../src/db.js';

describe('book collection API', () => {
  let db: ReturnType<typeof createDatabase>;
  let app: ReturnType<typeof createApp>;
  let server: ReturnType<ReturnType<typeof createApp>['listen']>;

  beforeEach(() => {
    db = createDatabase(':memory:');
    app = createApp(db);
    server = app.listen(0);
  });
  afterEach(() => {
    server.close();
    db.close();
  });

  it('reports healthy status', async () => {
    const response = await request(server).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok' });
  });

  it('creates and retrieves a book', async () => {
    const created = await request(server).post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '9780441013593' });
    expect(created.status).toBe(201);
    expect(created.body.id).toBe(1);
    const fetched = await request(server).get('/books/1');
    expect(fetched.status).toBe(200);
    expect(fetched.body.title).toBe('Dune');
  });

  it('validates required fields and filters by author', async () => {
    expect((await request(server).post('/books').send({ title: 'Untitled' })).status).toBe(400);
    await request(server).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    await request(server).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });
    const response = await request(server).get('/books?author=Frank%20Herbert');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0].title).toBe('Dune');
  });

  it('updates and deletes a book', async () => {
    await request(server).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
    const updated = await request(server).put('/books/1').send({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Dune Messiah');
    expect((await request(server).delete('/books/1')).status).toBe(204);
    expect((await request(server).get('/books/1')).status).toBe(404);
  });
});
