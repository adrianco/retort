import request from 'supertest';
import { app } from '../src/index';

describe('Book API', () => {
  beforeEach(async () => {
    // Clear the database before each test
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    await db.exec('DELETE FROM books');
    await db.exec('DELETE FROM sqlite_sequence WHERE name="books"');
  });

  it('should create a new book', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    expect(response.body).toHaveProperty('id');
    expect(response.body.title).toBe(bookData.title);
    expect(response.body.author).toBe(bookData.author);
    expect(response.body.year).toBe(bookData.year);
    expect(response.body.isbn).toBe(bookData.isbn);
  });

  it('should return 400 when creating a book without required fields', async () => {
    const bookData = {
      title: 'The Great Gatsby'
      // Missing author
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(400);

    expect(response.body).toHaveProperty('error');
  });

  it('should get all books', async () => {
    // First create a book
    await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      });

    const response = await request(app)
      .get('/books')
      .expect(200);

    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toHaveProperty('title', 'The Great Gatsby');
  });

  it('should filter books by author', async () => {
    // Create two books
    await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      });

    await request(app)
      .post('/books')
      .send({
        title: 'To Kill a Mockingbird',
        author: 'Harper Lee',
        year: 1960
      });

    const response = await request(app)
      .get('/books?author=Fitzgerald')
      .expect(200);

    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toHaveProperty('author', 'F. Scott Fitzgerald');
  });

  it('should get a single book by ID', async () => {
    // First create a book
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      });

    const bookId = createResponse.body.id;

    const response = await request(app)
      .get(`/books/${bookId}`)
      .expect(200);

    expect(response.body).toHaveProperty('title', 'The Great Gatsby');
    expect(response.body).toHaveProperty('author', 'F. Scott Fitzgerald');
  });

  it('should update a book', async () => {
    // First create a book
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      });

    const bookId = createResponse.body.id;

    const updateData = {
      title: 'The Great Gatsby - Revised Edition',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updateData)
      .expect(200);

    expect(response.body).toHaveProperty('title', updateData.title);
    expect(response.body).toHaveProperty('isbn', updateData.isbn);
  });

  it('should delete a book', async () => {
    // First create a book
    const createResponse = await request(app)
      .post('/books')
      .send({
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        year: 1925
      });

    const bookId = createResponse.body.id;

    const response = await request(app)
      .delete(`/books/${bookId}`)
      .expect(200);

    expect(response.body).toHaveProperty('message', 'Book deleted successfully');
  });

  it('should return 404 when trying to get a non-existent book', async () => {
    await request(app)
      .get('/books/999')
      .expect(404);
  });

  it('should return 404 when trying to update a non-existent book', async () => {
    const updateData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald'
    };

    await request(app)
      .put('/books/999')
      .send(updateData)
      .expect(404);
  });

  it('should return 404 when trying to delete a non-existent book', async () => {
    await request(app)
      .delete('/books/999')
      .expect(404);
  });
});
