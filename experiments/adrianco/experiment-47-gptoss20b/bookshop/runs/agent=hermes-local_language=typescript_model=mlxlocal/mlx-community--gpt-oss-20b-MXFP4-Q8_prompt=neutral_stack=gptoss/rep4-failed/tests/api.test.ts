import request from 'supertest';
import app from '../src/server';

describe('Book API', () => {
  let server: any;
  beforeAll(() => {
    server = app.listen(0); // random port
  });
  afterAll(() => {
    server.close();
  });

  test('health check', async () => {
    const res = await request(server).get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('create and get book', async () => {
    const book = { title: 'Test Book', author: 'Author', year: 2021, isbn: '123' };
    const createRes = await request(server).post('/books').send(book);
    expect(createRes.status).toBe(201);
    const created = createRes.body;
    expect(created).toMatchObject({ id: expect.any(Number), ...book });

    const getRes = await request(server).get(`/books/${created.id}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body).toEqual(created);
  });

  test('list books with filter', async () => {
    const book1 = { title: 'A', author: 'Common', year: 2000 };
    const book2 = { title: 'B', author: 'Other', year: 2001 };
    await request(server).post('/books').send(book1);
    await request(server).post('/books').send(book2);
    const res = await request(server).get('/books?author=Common');
    expect(res.status).toBe(200);
    expect(res.body).toEqual(expect.arrayContaining([expect.objectContaining({ author: 'Common' })]));
  });

  test('update book', async () => {
    const book = { title: 'Old', author: 'A', year: 1999 };
    const createRes = await request(server).post('/books').send(book);
    const id = createRes.body.id;
    const updateRes = await request(server).put(`/books/${id}`).send({ title: 'New', author: 'A', year: 2000 });
    expect(updateRes.status).toBe(200);
    expect(updateRes.body.title).toBe('New');
  });

  test('delete book', async () => {
    const book = { title: 'ToDelete', author: 'A' };
    const createRes = await request(server).post('/books').send(book);
    const id = createRes.body.id;
    const delRes = await request(server).delete(`/books/${id}`);
    expect(delRes.status).toBe(204);
    const getRes = await request(server).get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });
});
