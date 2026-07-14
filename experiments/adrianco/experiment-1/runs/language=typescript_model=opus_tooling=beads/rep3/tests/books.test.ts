import request from 'supertest';
import { createApp } from '../src/app';
import { createDb } from '../src/db';

function makeApp() {
  const db = createDb(':memory:');
  return createApp(db);
}

describe('Books API', () => {
  test('GET /health returns ok', async () => {
    const app = makeApp();
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('POST /books creates a book', async () => {
    const app = makeApp();
    const res = await request(app)
      .post('/books')
      .send({ title: 'Dune', author: 'Herbert', year: 1965, isbn: '123' });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: 1,
      title: 'Dune',
      author: 'Herbert',
      year: 1965,
      isbn: '123',
    });
  });

  test('POST /books requires title and author', async () => {
    const app = makeApp();
    const res1 = await request(app).post('/books').send({ author: 'X' });
    expect(res1.status).toBe(400);
    const res2 = await request(app).post('/books').send({ title: 'T' });
    expect(res2.status).toBe(400);
  });

  test('GET /books lists and filters by author', async () => {
    const app = makeApp();
    await request(app).post('/books').send({ title: 'A', author: 'Alice' });
    await request(app).post('/books').send({ title: 'B', author: 'Bob' });
    await request(app).post('/books').send({ title: 'C', author: 'Alice' });

    const all = await request(app).get('/books');
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const alice = await request(app).get('/books?author=Alice');
    expect(alice.status).toBe(200);
    expect(alice.body).toHaveLength(2);
    expect(alice.body.every((b: any) => b.author === 'Alice')).toBe(true);
  });

  test('GET /books/:id returns one book or 404', async () => {
    const app = makeApp();
    const created = await request(app)
      .post('/books')
      .send({ title: 'T', author: 'A' });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('T');

    const missing = await request(app).get('/books/9999');
    expect(missing.status).toBe(404);
  });

  test('PUT /books/:id updates a book', async () => {
    const app = makeApp();
    const created = await request(app)
      .post('/books')
      .send({ title: 'Old', author: 'A' });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: 'New' });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New');
    expect(res.body.author).toBe('A');
  });

  test('DELETE /books/:id removes a book', async () => {
    const app = makeApp();
    const created = await request(app)
      .post('/books')
      .send({ title: 'X', author: 'Y' });
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);
    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });
});
