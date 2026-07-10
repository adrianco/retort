const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
const dbPath = path.join(__dirname, 'books.db');
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

// GET /books - List all books with optional author filter
app.get('/books', (req, res) => {
  const { author } = req.query;
  
  let sql = 'SELECT * FROM books';
  const params = [];
  
  if (author) {
    sql += ' WHERE author = ?';
    params.push(author);
  }
  
  db.all(sql, params, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json({ books: rows });
  });
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
  const { id } = req.params;
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({ book: row });
  });
});

// POST /books - Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  const sql = 'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)';
  const params = [title, author, year, isbn];
  
  db.run(sql, params, function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        return res.status(400).json({ 
          error: 'ISBN must be unique' 
        });
      }
      return res.status(500).json({ error: err.message });
    }
    res.status(201).json({ 
      book: { id: this.lastID, title, author, year, isbn }
    });
  });
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req, res) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  const sql = 'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?';
  const params = [title, author, year, isbn, id];
  
  db.run(sql, params, function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        return res.status(400).json({ 
          error: 'ISBN must be unique' 
        });
      }
      return res.status(500).json({ error: err.message });
    }
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({ 
      book: { id, title, author, year, isbn }
    });
  });
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const { id } = req.params;
  
  db.run('DELETE FROM books WHERE id = ?', [id], function(err) {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({ message: 'Book deleted successfully' });
  });
});

// Handle 404 for undefined routes
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// Export for testing
module.exports = { app, db };

// Start server if not imported
if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}