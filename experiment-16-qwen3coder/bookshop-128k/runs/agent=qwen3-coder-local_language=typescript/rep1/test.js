const request = require('supertest');
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Create a fresh app for testing with a different port
const createTestApp = () => {
  const app = express();
  app.use(express.json());

  // Use a test database
  const dbPath = path.join(__dirname, 'test_books.db');
  const db = new sqlite3.Database(dbPath);

  // Create books table if it doesn't exist
  db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )`);
  });

  // Health check endpoint
  app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK', message: 'Book API is running' });
  });

  // POST /books - Create a new book
  app.post('/books', (req, res) => {
    const { title, author, year, isbn } = req.body;

    // Validation
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }

    const query = `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`;
    const params = [title, author, year || null, isbn || null];

    db.run(query, params, function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          return res.status(409).json({ 
            error: 'ISBN already exists' 
          });
        }
        return res.status(500).json({ 
          error: 'Database error' 
        });
      }
      
      res.status(201).json({
        id: this.lastID,
        title,
        author,
        year,
        isbn
      });
    });
  });

  // GET /books - List all books with optional author filter
  app.get('/books', (req, res) => {
    const { author } = req.query;
    let query = 'SELECT * FROM books';
    let params = [];

    if (author) {
      query += ' WHERE author LIKE ?';
      params = [`%${author}%`];
    }

    db.all(query, params, (err, rows) => {
      if (err) {
        return res.status(500).json({ 
          error: 'Database error' 
        });
      }
      res.json(rows);
    });
  });

  // GET /books/:id - Get a single book by ID
  app.get('/books/:id', (req, res) => {
    const id = req.params.id;
    const query = 'SELECT * FROM books WHERE id = ?';

    db.get(query, [id], (err, row) => {
      if (err) {
        return res.status(500).json({ 
          error: 'Database error' 
        });
      }
      
      if (!row) {
        return res.status(404).json({ 
          error: 'Book not found' 
        });
      }
      
      res.json(row);
    });
  });

  // PUT /books/:id - Update a book
  app.put('/books/:id', (req, res) => {
    const id = req.params.id;
    const { title, author, year, isbn } = req.body;

    // Validation
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }

    const query = `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`;
    const params = [title, author, year || null, isbn || null, id];

    db.run(query, params, function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          return res.status(409).json({ 
            error: 'ISBN already exists' 
          });
        }
        return res.status(500).json({ 
          error: 'Database error' 
        });
      }
      
      if (this.changes === 0) {
        return res.status(404).json({ 
          error: 'Book not found' 
        });
      }
      
      res.json({
        id: parseInt(id),
        title,
        author,
        year,
        isbn
      });
    });
  });

  // DELETE /books/:id - Delete a book
  app.delete('/books/:id', (req, res) => {
    const id = req.params.id;
    const query = 'DELETE FROM books WHERE id = ?';

    db.run(query, [id], function(err) {
      if (err) {
        return res.status(500).json({ 
          error: 'Database error' 
        });
      }
      
      if (this.changes === 0) {
        return res.status(404).json({ 
          error: 'Book not found' 
        });
      }
      
      res.json({ message: 'Book deleted successfully' });
    });
  });

  // Clean up database when server closes
  process.on('SIGINT', () => {
    db.close();
    process.exit(0);
  });

  return { app, db };
};

const { app } = createTestApp();
const port = 3001;

describe('Book API', () => {
  let server;

  beforeAll((done) => {
    server = app.listen(port, done);
  });

  afterAll((done) => {
    server.close(done);
  });

  test('GET /health should return OK', async () => {
    const response = await request(app)
      .get('/health')
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body).toEqual({
      status: 'OK',
      message: 'Book API is running'
    });
  });

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
      .expect(201)
      .expect('Content-Type', /json/);
    
    expect(response.body).toHaveProperty('id');
    expect(response.body.title).toBe(bookData.title);
    expect(response.body.author).toBe(bookData.author);
    expect(response.body.year).toBe(bookData.year);
    expect(response.body.isbn).toBe(bookData.isbn);
  });

  test('POST /books should reject missing required fields', async () => {
    const bookData = {
      title: 'The Great Gatsby'
      // Missing author
    };

    const response = await request(app)
      .post('/books')
      .send(bookData)
      .expect(400)
      .expect('Content-Type', /json/);
    
    expect(response.body).toHaveProperty('error');
  });

  test('GET /books should return all books', async () => {
    const response = await request(app)
      .get('/books')
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body).toBeInstanceOf(Array);
  });

  test('GET /books should support author filter', async () => {
    const response = await request(app)
      .get('/books?author=Fitzgerald')
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body).toBeInstanceOf(Array);
  });

  test('GET /books/:id should return a specific book (if exists)', async () => {
    // First create a book to get its ID
    const bookData = {
      title: '1984',
      author: 'George Orwell',
      year: 1948,
      isbn: '978-0-452-28423-4'
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
    
    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe(bookData.title);
    expect(response.body.author).toBe(bookData.author);
  });

  test('PUT /books/:id should update a book', async () => {
    // First create a book to get its ID
    const bookData = {
      title: 'Brave New World',
      author: 'Aldous Huxley',
      year: 1932,
      isbn: '978-0-06-085052-4'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    // Update the book
    const updatedData = {
      title: 'Brave New World - Updated',
      author: 'Aldous Huxley',
      year: 1932,
      isbn: '978-0-06-085052-4'
    };

    const response = await request(app)
      .put(`/books/${bookId}`)
      .send(updatedData)
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body.id).toBe(bookId);
    expect(response.body.title).toBe(updatedData.title);
  });

  test('DELETE /books/:id should delete a book', async () => {
    // First create a book to get its ID
    const bookData = {
      title: 'Pride and Prejudice',
      author: 'Jane Austen',
      year: 1813,
      isbn: '978-0-14-143951-8'
    };

    const createResponse = await request(app)
      .post('/books')
      .send(bookData)
      .expect(201);

    const bookId = createResponse.body.id;

    // Delete the book
    const response = await request(app)
      .delete(`/books/${bookId}`)
      .expect(200)
      .expect('Content-Type', /json/);
    
    expect(response.body.message).toBe('Book deleted successfully');

    // Verify the book is deleted
    const getResponse = await request(app)
      .get(`/books/${bookId}`)
      .expect(404);
  });
});