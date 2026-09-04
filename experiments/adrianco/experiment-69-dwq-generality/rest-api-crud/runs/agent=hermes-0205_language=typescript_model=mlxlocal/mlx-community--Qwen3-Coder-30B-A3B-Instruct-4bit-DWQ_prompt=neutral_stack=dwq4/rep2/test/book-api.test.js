const request = require('supertest');
const { app, db } = require('../src/app');
const sqlite3 = require('sqlite3').verbose();

// Create a test database file for testing
const testDbPath = './test.db';

// Clear the database before tests
beforeAll((done) => {
  // Clear all books from the database
  db.serialize(() => {
    db.run('DELETE FROM books', function(err) {
      if (err) {
        console.error('Error clearing database:', err);
        done(err);
      } else {
        // Reset the auto-increment counter
        db.run('DELETE FROM sqlite_sequence WHERE name = "books"', function(err) {
          if (err) {
            console.error('Error resetting sequence:', err);
            done(err);
          } else {
            done();
          }
        });
      }
    });
  });
});

describe('Book API', () => {
  test('Health check endpoint', async () => {
    const response = await request(app)
      .get('/health')
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body).toEqual({
      status: 'OK',
      message: 'Book API is running'
    });
  });

  test('Create a new book', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201)
      .expect('Content-Type', /json/);

    expect(response.body).toEqual({
      id: expect.any(Number),
      title: bookData.title,
      author: bookData.author,
      year: bookData.year,
      isbn: bookData.isbn
    });

    // Verify the book was actually saved
    const savedBook = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM books WHERE id = ?', [response.body.id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    expect(savedBook).toEqual({
      id: response.body.id,
      title: bookData.title,
      author: bookData.author,
      year: bookData.year,
      isbn: bookData.isbn
    });
  });

  test('Create a book without required fields should fail', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      // Missing author field
      year: 1925
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(400);

    expect(response.body).toEqual({
      error: 'Title and author are required fields'
    });
  });

  test('Get all books', async () => {
    // Add some test books
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

    const response = await request(app)
      .get('/books')
      .expect(200)
      .expect('Content-Type', /json/);

    expect(response.body).toHaveLength(2);
    expect(response.body[0]).toEqual({
      id: expect.any(Number),
      title: book1.title,
      author: book1.author,
      year: book1.year,
      isbn: book1.isbn
    });
    expect(response.body[1]).toEqual({
      id: expect.any(Number),
      title: book2.title,
      author: book2.author,
      year: book2.year,
      isbn: book2.isbn
    });
  });

  test('Get books filtered by author', async () => {
    // Add some test books
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

    const book3 = {
      title: 'The Catcher in the Rye',
      author: 'J.D. Salinger',
      year: 1951,
      isbn: '978-0-316-76948-0'
    };

    await request(app).post('/books').send(book1);
    await request(app).post('/books').send(book2);
    await request(app).post('/books').send(book3);

    const response = await request(app)
      .get('/books?author=Fitzgerald')
      .expect(200)
      .expect('Content-Type', /json/);

    expect(response.body).toHaveLength(1);
    expect(response.body[0]).toEqual({
      id: expect.any(Number),
      title: book1.title,
      author: book1.author,
      year: book1.year,
      isbn: book1.isbn
    });
  });

  test('Get a single book by ID', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    const response = await request(app)
      .get(`/books/${bookId}`)
      .expect(200)
      .expect('Content-Type', /json/);

    expect(response.body).toEqual({
      id: bookId,
      title: bookData.title,
      author: bookData.author,
      year: bookData.year,
      isbn: bookData.isbn
    });
  });

  test('Get a non-existent book should return 404', async () => {
    const response = await request(app)
      .get('/books/999')
      .expect(404);

    expect(response.body).toEqual({
      error: 'Book not found'
    });
  });

  test('Update a book', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    const updateData = {
      title: 'Updated Title',
      author: 'Updated Author',
      year: 1926,
      isbn: '978-0-7432-7356-6'
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updateData)
      .expect(200)
      .expect('Content-Type', /json/);

    expect(response.body).toEqual({
      id: bookId,
      title: updateData.title,
      author: updateData.author,
      year: updateData.year,
      isbn: updateData.isbn
    });

    // Verify the update was actually saved
    const savedBook = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM books WHERE id = ?', [bookId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    expect(savedBook).toEqual({
      id: bookId,
      title: updateData.title,
      author: updateData.author,
      year: updateData.year,
      isbn: updateData.isbn
    });
  });

  test('Update a non-existent book should return 404', async () => {
    const updateData = {
      title: 'Updated Title',
      author: 'Updated Author',
      year: 1926,
      isbn: '978-0-7432-7356-6'
    };

    const response = await request(app)
      .put('/books/999')
      .send(updateData)
      .expect(404);

    expect(response.body).toEqual({
      error: 'Book not found'
    });
  });

  test('Update a book without required fields should fail', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    const updateData = {
      title: 'Updated Title',
      // Missing author field
      year: 1926
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updateData)
      .expect(400);

    expect(response.body).toEqual({
      error: 'Title and author are required fields'
    });
  });

  test('Delete a book', async () => {
    const bookData = {
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      year: 1925,
      isbn: '978-0-7432-7356-5'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    const response = await request(app)
      .delete(`/books/${bookId}`)
      .expect(200)
      .expect('Content-Type', /json/);

    expect(response.body).toEqual({
      message: 'Book deleted successfully'
    });

    // Verify the book was actually deleted
    const deletedBook = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM books WHERE id = ?', [bookId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    expect(deletedBook).toBeUndefined();
  });

  test('Delete a non-existent book should return 404', async () => {
    const response = await request(app)
      .delete('/books/999')
      .expect(404);

    expect(response.body).toEqual({
      error: 'Book not found'
    });
  });
});