import request from 'supertest';
import { createApp } from '../src/app';
import { BookStore } from '../src/db';

describe('Books API', () => {
  let store: BookStore;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    store = new BookStore(':memory:');
    app = createApp(store);
  });

  afterEach(() => {
    store.close();
  });

  describe('GET /health', () => {
    it('returns 200 with status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });
  });

  describe('POST /books', () => {
    it('creates a book and returns 201 with the new book', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert', year: 1965, isbn: '978-0441172719' });
      expect(res.status).toBe(201);
      expect(res.body).toMatchObject({
        id: expect.any(Number),
        title: 'Dune',
        author: 'Frank Herbert',
        year: 1965,
        isbn: '978-0441172719',
      });
    });

    it('creates a book without optional fields', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Title', author: 'Author' });
      expect(res.status).toBe(201);
      expect(res.body.year).toBeNull();
      expect(res.body.isbn).toBeNull();
    });

    it('returns 400 when title is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ author: 'Anonymous' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/title/);
    });

    it('returns 400 when author is missing', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'Untitled' });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/author/);
    });

    it('returns 400 when title is empty string', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: '   ', author: 'Someone' });
      expect(res.status).toBe(400);
    });

    it('returns 400 when year is not an integer', async () => {
      const res = await request(app)
        .post('/books')
        .send({ title: 'T', author: 'A', year: 'not a year' });
      expect(res.status).toBe(400);
    });
  });

  describe('GET /books', () => {
    beforeEach(async () => {
      await request(app).post('/books').send({ title: 'Dune', author: 'Frank Herbert' });
      await request(app).post('/books').send({ title: 'Foundation', author: 'Isaac Asimov' });
      await request(app).post('/books').send({ title: 'I, Robot', author: 'Isaac Asimov' });
    });

    it('lists all books', async () => {
      const res = await request(app).get('/books');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(3);
    });

    it('filters by author', async () => {
      const res = await request(app).get('/books?author=Isaac Asimov');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
      expect(res.body.every((b: { author: string }) => b.author === 'Isaac Asimov')).toBe(true);
    });

    it('returns empty array when author filter has no matches', async () => {
      const res = await request(app).get('/books?author=Nobody');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });
  });

  describe('GET /books/:id', () => {
    it('returns a book by id', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert' });
      const res = await request(app).get(`/books/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Dune');
    });

    it('returns 404 for unknown id', async () => {
      const res = await request(app).get('/books/9999');
      expect(res.status).toBe(404);
    });

    it('returns 400 for invalid id', async () => {
      const res = await request(app).get('/books/not-a-number');
      expect(res.status).toBe(400);
    });
  });

  describe('PUT /books/:id', () => {
    it('updates an existing book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: 'Dune Messiah', author: 'Frank Herbert', year: 1969 });
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Dune Messiah');
      expect(res.body.year).toBe(1969);
    });

    it('returns 404 when updating unknown id', async () => {
      const res = await request(app)
        .put('/books/9999')
        .send({ title: 'X', author: 'Y' });
      expect(res.status).toBe(404);
    });

    it('returns 400 when updating with invalid body', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert' });
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: '' });
      expect(res.status).toBe(400);
    });
  });

  describe('DELETE /books/:id', () => {
    it('deletes an existing book', async () => {
      const created = await request(app)
        .post('/books')
        .send({ title: 'Dune', author: 'Frank Herbert' });
      const del = await request(app).delete(`/books/${created.body.id}`);
      expect(del.status).toBe(204);
      const get = await request(app).get(`/books/${created.body.id}`);
      expect(get.status).toBe(404);
    });

    it('returns 404 when deleting unknown id', async () => {
      const res = await request(app).delete('/books/9999');
      expect(res.status).toBe(404);
    });
  });
});
