import { afterEach, describe, expect, it } from 'vitest';
import Database from 'better-sqlite3';
import request from 'supertest';
import { createApp } from '../src/app.js';

const databases: Database.Database[] = [];
function setup() {
  const db = new Database(':memory:');
  databases.push(db);
  return request(createApp(db));
}
afterEach(() => { for (const db of databases.splice(0)) db.close(); });

describe('books API', () => {
  it('creates books and filters by author', async () => {
    const api = setup();
    const created = await api.post('/books').send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '123' });
    expect(created.status).toBe(201);
    expect(created.body).toMatchObject({ title: 'Dune', author: 'Frank Herbert', year: 1965 });
    await api.post('/books').send({ title: 'Other', author: 'Someone' });
    const filtered = await api.get('/books?author=Frank%20Herbert');
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].isbn).toBe('123');
  });

  it('requires title and author', async () => {
    const api = setup();
    expect((await api.post('/books').send({ title: 'Untitled' })).status).toBe(400);
    expect((await api.post('/books').send({ title: ' ', author: 'A' })).status).toBe(400);
  });

  it('gets, updates, deletes, and reports missing records', async () => {
    const api = setup();
    const created = await api.post('/books').send({ title: 'Old', author: 'Author' });
    const id = created.body.id;
    expect((await api.get(`/books/${id}`)).status).toBe(200);
    expect((await api.put(`/books/${id}`).send({ title: 'New', author: 'Author', year: 2020 })).body.title).toBe('New');
    expect((await api.delete(`/books/${id}`)).status).toBe(204);
    expect((await api.get(`/books/${id}`)).status).toBe(404);
  });

  it('exposes a health check', async () => {
    expect((await setup().get('/health')).body).toEqual({ status: 'ok' });
  });
});
