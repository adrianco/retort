import request from 'supertest';
import { app } from './app';

describe('Book API', () => {
  it('should return health check', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'OK' });
  });

  it('should create a new book', async () => {
    const newBook = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app).post('/books').send(newBook);
    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('title', newBook.title);
    expect(response.body).toHaveProperty('author', newBook.author);
    expect(response.body).toHaveProperty('year', newBook.year);
    expect(response.body).toHaveProperty('isbn', newBook.isbn);
  });

  it('should reject book creation without title or author', async () => {
    const response = await request(app).post('/books').send({
      title: 'The Great Gatsby'
      // Missing author
    });
    expect(response.status).toBe(400);
    expect(response.body).toHaveProperty('error');
  });

  it('should get all books', async () => {
    // First create a book
    await request(app).post('/books').send({
      title: '1984',
      author: 'George Orwell'
    });

    // Then fetch all books
    const response = await request(app).get('/books');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toHaveProperty('title', '1984');
    expect(response.body[0]).toHaveProperty('author', 'George Orwell');
  });

  it('should filter books by author', async () => {
    // Create two books with different authors
    await request(app).post('/books').send({
      title: '1984',
      author: 'George Orwell'
    });

    await request(app).post('/books').send({
      title: 'Animal Farm',
      author: 'George Orwell'
    });

    await request(app).post('/books').send({
      title: 'To Kill a Mockingbird',
      author: 'Harper Lee'
    });

    // Filter by author
    const response = await request(app).get('/books?author=George');
    expect(response.status).toBe(200);
    expect(response.body).toHaveLength(2);
  });

  it('should get a single book by ID', async () => {
    // Create a book first
    const createResponse = await request(app).post('/books').send({
      title: 'To Kill a Mockingbird',
      author: 'Harper Lee'
    });

    const bookId = createResponse.body.id;

    // Get the book by ID
    const response = await request(app).get(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('title', 'To Kill a Mockingbird');
    expect(response.body).toHaveProperty('author', 'Harper Lee');
  });

  it('should update a book', async () => {
    // Create a book first
    const createResponse = await request(app).post('/books').send({
      title: 'Dune',
      author: 'Frank Herbert'
    });

    const bookId = createResponse.body.id;

    // Update the book
    const updateData = {
      title: 'Dune Messiah',
      author: 'Frank Herbert',
      year: 1969
    };

    const response = await request(app).put(`/books/${bookId}`).send(updateData);
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('title', 'Dune Messiah');
    expect(response.body).toHaveProperty('year', 1969);
  });

  it('should delete a book', async () => {
    // Create a book first
    const createResponse = await request(app).post('/books').send({
      title: 'The Catcher in the Rye',
      author: 'J.D. Salinger'
    });

    const bookId = createResponse.body.id;

    // Delete the book
    const response = await request(app).delete(`/books/${bookId}`);
    expect(response.status).toBe(204);

    // Verify the book is deleted
    const getResponse = await request(app).get(`/books/${bookId}`);
    expect(getResponse.status).toBe(404);
  });
});
