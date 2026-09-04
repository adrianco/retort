const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 3000;

// Middleware
app.use(express.json());

// Initialize database
const db = new sqlite3.Database(':memory:'); // Using in-memory database for simplicity

// Create books table
db.serialize(() => {
  db.run(`CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy' });
});

// Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: 'Title and author are required fields'
    });
  }
  
  const stmt = db.prepare(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`);
  stmt.run([title, author, year || null, isbn || null], function(err) {
    if (err) {
      return res.status(500).json({
        error: 'Failed to create book',
        details: err.message
      });
    }
    
    // Return the created book with its ID
    db.get('SELECT * FROM books WHERE id = ?', [this.lastID], (err, row) => {
      if (err) {
        return res.status(500).json({
          error: 'Failed to retrieve created book',
          details: err.message
        });
      }
      res.status(201).json(row);
    });
  });
});

// Get all books with optional author filter
app.get('/books', (req, res) => {
  const { author } = req.query;
  
  let sql = 'SELECT * FROM books';
  let params = [];
  
  if (author) {
    sql = 'SELECT * FROM books WHERE author = ?';
    params = [author];
  }
  
  db.all(sql, params, (err, rows) => {
    if (err) {
      return res.status(500).json({
        error: 'Failed to retrieve books',
        details: err.message
      });
    }
    res.json(rows);
  });
});

// Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = req.params.id;
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({
        error: 'Failed to retrieve book',
        details: err.message
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

// Update a book
app.put('/books/:id', (req, res) => {
  const id = req.params.id;
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: 'Title and author are required fields'
    });
  }
  
  const stmt = db.prepare(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`);
  stmt.run([title, author, year || null, isbn || null, id], function(err) {
    if (err) {
      return res.status(500).json({
        error: 'Failed to update book',
        details: err.message
      });
    }
    
    if (this.changes === 0) {
      return res.status(404).json({
        error: 'Book not found'
      });
    }
    
    // Return the updated book
    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) {
        return res.status(500).json({
          error: 'Failed to retrieve updated book',
          details: err.message
        });
      }
      res.json(row);
    });
  });
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  const id = req.params.id;
  
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  stmt.run([id], function(err) {
    if (err) {
      return res.status(500).json({
        error: 'Failed to delete book',
        details: err.message
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

// Handle 404 for undefined routes
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found'
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Something went wrong!',
    details: err.message
  });
});

app.listen(port, () => {
  console.log(`Book API server running at http://localhost:${port}`);
});

module.exports = app;