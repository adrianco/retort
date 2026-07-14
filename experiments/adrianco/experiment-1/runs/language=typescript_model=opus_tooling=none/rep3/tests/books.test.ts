import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

function makeApp() {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Books API', () => {
  it('GET /health returns ok', async () => {
    const app = makeApp();
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  it('POST /books creates a book and GET /books/:id returns it', async () => {
    const app = makeApp();
    const create = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Herbert', year: 1965, isbn: '978-0441013593' });
    expect(create.status).toBe(201);
    expect(create.body.id).toBeDefined();
    expect(create.body.title).toBe('Dune');

    const get = await request(app).get(`/books/${create.body.id}`);
    expect(get.status).toBe(200);
    expect(get.body.author).toBe('Herbert');
  });

  it('POST /books rejects missing title', async () => {
    const app = makeApp();
    const res = await request(app).post('/books').send({ author: 'Someone' });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/);
  });

  it('GET /books supports author filter', async () => {
    const app = makeApp();
    await request(app).post('/books').send({ title: 'A', author: 'X' });
    await request(app).post('/books').send({ title: 'B', author: 'Y' });
    await request(app).post('/books').send({ title: 'C', author: 'X' });

    const all = await request(app).get('/books');
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get('/books').query({ author: 'X' });
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(2);
    expect(filtered.body.every((b: any) => b.author === 'X')).toBe(true);
  });

  it('PUT /books/:id updates a book', async () => {
    const app = makeApp();
    const create = await request(app).post('/books').send({ title: 'Old', author: 'A' });
    const id = create.body.id;

    const upd = await request(app).put(`/books/${id}`).send({ title: 'New' });
    expect(upd.status).toBe(200);
    expect(upd.body.title).toBe('New');
    expect(upd.body.author).toBe('A');
  });

  it('DELETE /books/:id removes a book', async () => {
    const app = makeApp();
    const create = await request(app).post('/books').send({ title: 'T', author: 'A' });
    const id = create.body.id;

    const del = await request(app).delete(`/books/${id}`);
    expect(del.status).toBe(204);

    const get = await request(app).get(`/books/${id}`);
    expect(get.status).toBe(404);
  });

  it('GET /books/:id returns 404 for unknown id', async () => {
    const app = makeApp();
    const res = await request(app).get('/books/99999');
    expect(res.status).toBe(404);
  });
});
