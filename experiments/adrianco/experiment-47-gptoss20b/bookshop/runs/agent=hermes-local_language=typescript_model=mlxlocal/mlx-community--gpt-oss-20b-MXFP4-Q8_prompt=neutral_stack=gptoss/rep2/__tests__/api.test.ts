import request from 'supertest';
import { server } from '../src/index';

describe('Book API', () => {
  let agent: request.SuperAgentTest;
  beforeAll(() => {
    agent = request.agent(server);
  });

  test('health check', async () => {
    const res = await agent.get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok' });
  });

  test('create book', async () => {
    const book = { title: 'Test Book', author: 'John Doe', year: 2021, isbn: '12345' };
    const res = await agent.post('/books').send(book);
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject(book);
    expect(res.body).toHaveProperty('id');
  });

  test('list books', async () => {
    const res = await agent.get('/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThan(0);
  });

  test('filter by author', async () => {
    const res = await agent.get('/books').query({ author: 'John Doe' });
    expect(res.status).toBe(200);
    expect(res.body).toBeInstanceOf(Array);
    res.body.forEach((b: any) => {
      expect(b.author).toBe('John Doe');
    });
  });

  test('get single book', async () => {
    const createRes = await agent.post('/books').send({ title: 'Another', author: 'Jane', year: 2020 });
    const id = createRes.body.id;
    const res = await agent.get(`/books/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(id);
  });

  test('update book', async () => {
    const createRes = await agent.post('/books').send({ title: 'Update', author: 'U', year: 2019 });
    const id = createRes.body.id;
    const res = await agent.put(`/books/${id}`).send({ title: 'Updated', author: 'U', year: 2022 });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Updated');
  });

  test('delete book', async () => {
    const createRes = await agent.post('/books').send({ title: 'Delete', author: 'D', year: 2018 });
    const id = createRes.body.id;
    const delRes = await agent.delete(`/books/${id}`);
    expect(delRes.status).toBe(204);
    const getRes = await agent.get(`/books/${id}`);
    expect(getRes.status).toBe(404);
  });
});
