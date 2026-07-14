import { describe, it } from 'mocha';
import supertest = require('supertest');
import { createApp } from '../src/server';

describe('Unit Tests - Book Collection API', function () {
  describe('Input trimming', function () {
    it('should produce a book object with trimmed whitespace from title and author', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ title: '  Book Title  ', author: '  Author Name  ', year: 2020, isbn: 'test' });

      if (res.status !== 201) throw new Error(`Expected 201, got ${res.status}`);
      if (res.body.title !== 'Book Title') throw new Error(`Expected trimmed title, got: ${res.body.title}`);
      if (res.body.author !== 'Author Name') throw new Error(`Expected trimmed author, got: ${res.body.author}`);
    });
  });

  describe('Default values', function () {
    it('should accept books with missing year and isbn', async () => {
      const app = createApp();
      const res = await supertest(app)
        .post('/books')
        .send({ title: 'Minimal Book', author: 'Author' });

      if (res.status !== 201) throw new Error(`Expected 201, got ${res.status} body: ${JSON.stringify(res.body)}`);
      const currentYear = new Date().getFullYear();
      if (res.body.year !== currentYear) throw new Error(`Expected year ${currentYear}, got: ${res.body.year}`);
      if (res.body.isbn !== '') throw new Error(`Expected empty isbn, got: ${res.body.isbn}`);
    });
  });

  describe('Integration Tests - end-to-end workflows', function () {
    it('should support a full create-read-update-delete lifecycle', async () => {
      const app = createApp();
      const request = supertest(app);

      // 1. Create
      const createRes = await request.post('/books').send({
        title: 'Clean Code',
        author: 'Robert C. Martin',
        year: 2008,
        isbn: '978-0132350884',
      });
      if (createRes.status !== 201) throw new Error(`Create failed: ${createRes.status}`);
      const bookId = createRes.body.id;

      // 2. Read
      const getRes = await request.get(`/books/${bookId}`);
      if (getRes.status !== 200) throw new Error(`Read failed: ${getRes.status}`);
      if (getRes.body.title !== 'Clean Code') throw new Error('Read returned wrong book');

      // 3. Update
      const updateRes = await request.put(`/books/${bookId}`).send({
        title: 'Clean Code: A Handbook',
        author: 'Robert C. Martin',
        year: 2009,
        isbn: '978-0132350884',
      });
      if (updateRes.status !== 200) throw new Error(`Update failed: ${updateRes.status}`);
      if (updateRes.body.title !== 'Clean Code: A Handbook') throw new Error('Update did not change title');

      // 4. List all books
      const listRes = await request.get('/books');
      if (listRes.status !== 200) throw new Error(`List failed: ${listRes.status}`);
      if (listRes.body.length !== 1) throw new Error('Expected 1 book in list');
      if (listRes.body[0].title !== 'Clean Code: A Handbook') throw new Error('List returned stale data');

      // 5. Delete
      const deleteRes = await request.delete(`/books/${bookId}`);
      if (deleteRes.status !== 200) throw new Error(`Delete failed: ${deleteRes.status}`);
      if (deleteRes.body.id !== bookId) throw new Error('Delete returned wrong book');

      // 6. Verify deletion
      const afterDelete = await request.get('/books');
      if (afterDelete.body.length !== 0) throw new Error('Expected 0 books after deletion');
    });

    it('should handle concurrent book creation with unique IDs', async () => {
      const app = createApp();
      const request = supertest(app);

      const books = [
        { title: 'Book A', author: 'Author A', year: 2001, isbn: '1001' },
        { title: 'Book B', author: 'Author A', year: 2002, isbn: '1002' },
        { title: 'Book C', author: 'Author B', year: 2003, isbn: '1003' },
        { title: 'Book D', author: 'Author B', year: 2004, isbn: '1004' },
        { title: 'Book E', author: 'Author C', year: 2005, isbn: '1005' },
      ];

      const results = await Promise.all(
        books.map(book => request.post('/books').send(book))
      );

      // All should succeed with 201
      for (let i = 0; i < results.length; i++) {
        if (results[i].status !== 201) {
          throw new Error(`Book ${i} creation failed: ${results[i].status} ${JSON.stringify(results[i].body)}`);
        }
        if (results[i].body.id === 0) throw new Error(`Expected non-zero ID for book ${i}`);
      }

      // Verify all IDs are unique
      const ids = results.map(r => r.body.id);
      const uniqueIds = new Set(ids);
      if (uniqueIds.size !== ids.length) {
        throw new Error('Duplicate IDs generated: ' + JSON.stringify(ids));
      }

      // Verify listing
      const listRes = await request.get('/books');
      if (listRes.body.length !== 5) throw new Error(`Expected 5 books, got ${listRes.body.length}`);
    });
  });
});
