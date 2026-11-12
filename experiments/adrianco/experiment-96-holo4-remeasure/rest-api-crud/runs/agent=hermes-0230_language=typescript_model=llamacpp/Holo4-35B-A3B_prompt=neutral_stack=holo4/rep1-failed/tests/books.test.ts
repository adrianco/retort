import request from 'supertest';
import { app } from './server';

const API = request(app);

describe('Health Check', () => {
  it('GET /health returns 200 with OK status', async () => {
    const res = await API.get('/health');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('status', 'OK');
    expect(res.body).toHaveProperty('timestamp');
  });
});

describe('Books API', () => {
  describe('POST /books', () => {
    it('creates a new book and returns 201', async () => {
      const res = await API
        .post('/books')
        .send({ title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', year: 1925, isbn: '978-0743273565' });
      expect(res.status).toBe(201);
      expect(res.body).toHaveProperty('id');
      expect(res.body.title).toBe('The Great Gatsby');
      expect(res.body.author).toBe('F. Scott Fitzgerald');
      expect(res.body.year).toBe(1925);
      expect(res.body.isbn).toBe('978-0743273565');
    });

    it('returns 400 when title is missing', async () => {
      const res = await API
        .post('/books')
        .send({ author: 'Test', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Title is required');
    });

    it('returns 400 when author is missing', async () => {
      const res = await API
        .post('/books')
        .send({ title: 'Test Book', year: 2020, isbn: '123' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('Author is required');
    });

    it('returns 409 when ISBN already exists', async () => {
      await API.post('/books').send({ title: 'Dup', author: 'Auth', year: 2020, isbn: 'dup-isbn' });
      const res = await API
        .post('/books')
        .send({ title: 'Dup2', author: 'Auth2', year: 2021, isbn: 'dup-isbn' });
      expect(res.status).toBe(409);
    });
  });

  describe('GET /books', () => {
    it('lists all books', async () => {
      const res = await API.get('/books');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.length).toBeGreaterThan(0);
    });

    it('filters books by author', async () => {
      const res = await API.get('/books').query({ author: 'F. Scott Fitzgerald' });
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body)).toBe(true);
      expect(res.body.every((b: any) => b.author === 'F. Scott Fitzgerald')).toBe(true);
    });
  });

  describe('GET /books/:id', () => {
    it('returns a book by ID', async () => {
      const res = await API.get('/books/1');
      expect(res.status).toBe(200);
      expect(res.body.id).toBe(1);
    });

    it('returns 404 for non-existent book', async () => {
      const res = await API.get('/books/99999');
      expect(res.status).toBe(404);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates a book', async () => {
      const res = await API
        .put('/books/1')
        .send({ title: 'The Great Gatsby (Updated)' });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('The Great Gatsby (Updated)');
    });

    it('returns 404 for non-existent book', async () => {
      const res = await API.put('/books/99999').send({ title: 'Nope' });
      expect(res.status).toBe(404);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes a book and returns 204', async () => {
      const res = await API.delete('/books/1');
      expect(res.status).toBe(204);
    });

    it('returns 404 for non-existent book', async () => {
      const res = await API.delete('/books/99999');
      expect(res.status).toBe(404);
    });
  });
});
