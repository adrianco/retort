const request = require('supertest');
const app = require('./server');

describe('Book API', () => {
  let server;
  
  beforeAll((done) => {
    // Start the server for testing
    const PORT = 3001;
    server = app.listen(PORT, done);
  });

  afterAll((done) => {
    // Close the server after tests
    server.close(done);
  });

  // Test health check endpoint
  test('GET /health should return OK', async () => {
    const response = await request(app).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      status: 'OK',
      message: 'Book API is running'
    });
  });

  // Test creating a book
  test('POST /books should create a new book', async () => {
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

  // Test creating a book without required fields
  test('POST /books should reject missing required fields', async () => {
    const bookData = {
      title: 'The Great Gatsby'
      // Missing author
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(400);

    expect(response.body).toHaveProperty('error');
    expect(response.body.error).toBe('Title and author are required');
  });

  // Test getting all books
  test('GET /books should return all books', async () => {
    // First create a book
    const bookData = {
      title: '1984',
      author: 'George Orwell',
      year: 1948
    };

    await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    // Then fetch all books
    const response = await request(app).get('/books');
    expect(response.status).toBe(200);
    expect(response.body).toBeInstanceOf(Array);
    expect(response.body.length).toBeGreaterThan(0);
  });

  // Test getting a book by ID
  test('GET /books/:id should return a specific book', async () => {
    // First create a book to get its ID
    const bookData = {
      title: 'To Kill a Mockingbird',
      author: 'Harper Lee',
      year: 1960
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    // Then fetch that specific book
    const response = await request(app).get(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe(bookData.title);
    expect(response.body.author).toBe(bookData.author);
  });

  // Test updating a book
  test('PUT /books/:id should update a book', async () => {
    // First create a book
    const bookData = {
      title: 'Brave New World',
      author: 'Aldous Huxley',
      year: 1932
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    // Then update the book
    const updateData = {
      title: 'Brave New World - Updated',
      author: 'Aldous Huxley',
      year: 1932,
      isbn: '978-0-06-085052-4'
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updateData)
      .expect(200);

    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe(updateData.title);
    expect(response.body.author).toBe(updateData.author);
    expect(response.body.isbn).toBe(updateData.isbn);
  });

  // Test deleting a book
  test('DELETE /books/:id should delete a book', async () => {
    // First create a book
    const bookData = {
      title: 'Pride and Prejudice',
      author: 'Jane Austen',
      year: 1813
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    // Then delete the book
    const response = await request(app).delete(`/books/${bookId}`);
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ message: 'Book deleted successfully' });

    // Verify the book is deleted by trying to fetch it
    const fetchResponse = await request(app).get(`/books/${bookId}`);
    expect(fetchResponse.status).toBe(404);
  });

  // Test error handling for non-existent book
  test('GET /books/:id should return 404 for non-existent book', async () => {
    const response = await request(app).get('/books/999999');
    expect(response.status).toBe(404);
    expect(response.body).toHaveProperty('error');
  });

  // Test author filter
  test('GET /books should support author filter', async () => {
    // Create books with different authors
    await request(app)
      .post('/books')
      .send({
        title: 'Book 1',
        author: 'Test Author',
        year: 2020
      })
      .expect(201);

    await request(app)
      .post('/books')
      .send({
        title: 'Book 2',
        author: 'Another Author',
        year: 2021
      })
      .expect(201);

    // Filter by author
    const response = await request(app).get('/books?author=Test Author');
    expect(response.status).toBe(200);
    expect(response.body).toBeInstanceOf(Array);
    expect(response.body.length).toBe(1);
    expect(response.body[0].author).toBe('Test Author');
  });
});