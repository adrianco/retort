const request = require('supertest');
const { app, initDB } = require('./src/index.js');

describe('Book API Tests', () => {
  beforeAll(async () => {
    await initDB();
  });

  beforeEach(async () => {
    // Clear all books before each test
    const db = require('sqlite3').verbose();
    const testDb = new db.Database('./books.db');
    await new Promise((resolve, reject) => {
      testDb.serialize(() => {
        testDb.run('DELETE FROM books', (err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    });
    testDb.close();
  });

  test('Health check endpoint should return OK', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('status', 'OK');
  });

  test('POST /books should create a new book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(newBook)
      .expect(201);

    expect(response.body).toHaveProperty('title', 'The Great Gatsby');
    expect(response.body).toHaveProperty('author', 'F. Scott Fitzgerald');
    expect(response.body).toHaveProperty('year', 1925);
    expect(response.body).toHaveProperty('isbn', '978-0-7432-7356-5');
  });

  test('POST /books should reject missing title or author', async () => {
    const bookWithoutTitle = {
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(bookWithoutTitle)
      .expect(400);

    expect(response.body).toHaveProperty('error');

    const bookWithoutAuthor = {
      title: 'The Great Gatsby',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response2 = await request(app)
      .post('/books')
      .send(bookWithoutAuthor)
      .expect(400);

    expect(response2.body).toHaveProperty('error');
  });

  test('GET /books should list all books', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    await request(app)
      .post('/books')
      .send(newBook);

    const response = await request(app).get('/books');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toHaveProperty('title', 'The Great Gatsby');
  });

  test('GET /books with author filter should work', async () => {
    const book1 = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const book2 = {
      title: 'To Kill a Mockingbird',
      author: 'Harper Lee',
      year: 1960,
      isbn: '978-0-06-112008-4'
    };

    await request(app).post('/books').send(book1);
    await request(app).post('/books').send(book2);

    const response = await request(app).get('/books?author=F. Scott Fitzgerald');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toHaveProperty('title', 'The Great Gatsby');
  });

  test('GET /books/:id should return a single book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(newBook)
      .expect(201);

    const bookId = createResponse.body.id;

    const response = await request(app).get(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('title', 'The Great Gatsby');
  });

  test('GET /books/:id should return 404 for non-existent book', async () => {
    const response = await request(app).get('/books/999');
    expect(response.status).toBe(404);
    expect(response.body).toHaveProperty('error', 'Book not found');
  });

  test('PUT /books/:id should update a book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(newBook)
      .expect(201);

    const bookId = createResponse.body.id;

    const updatedBook = {
      title: 'The Great Gatsby - Updated',
      author: 'F. Scott Fitzgerald',
      year: 1926,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updatedBook)
      .expect(200);

    expect(response.body).toHaveProperty('title', 'The Great Gatsby - Updated');
    expect(response.body).toHaveProperty('year', 1926);
  });

  test('PUT /books/:id should return 404 for non-existent book', async () => {
    const updatedBook = {
      title: 'The Great Gatsby - Updated',
      author: 'F. Scott Fitzgerald',
      year: 1926,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .put('/books/999')
      .send(updatedBook)
      .expect(404);

    expect(response.body).toHaveProperty('error', 'Book not found');
  });

  test('DELETE /books/:id should delete a book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(newBook)
      .expect(201);

    const bookId = createResponse.body.id;

    const response = await request(app)
      .delete(`/books/${bookId}`)
      .expect(200);

    expect(response.body).toHaveProperty('message', 'Book deleted successfully');

    // Verify it's actually deleted
    const getResponse = await request(app).get(`/books/${bookId}`);
    expect(getResponse.status).toBe(404);
  });

  test('DELETE /books/:id should return 404 for non-existent book', async () => {
    const response = await request(app)
      .delete('/books/999')
      .expect(404);

    expect(response.body).toHaveProperty('error', 'Book not found');
  });
});