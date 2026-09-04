const express = require('express');
const sqlite3 = require('sqlite3');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
const db = new sqlite3.Database(':memory:'); // In-memory database for simplicity

// Create books table
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

// Get all books with optional author filter
app.get('/books', (req, res) => {
  const author = req.query.author;
  
  let query = 'SELECT * FROM books';
  let params = [];
  
  if (author) {
    query += ' WHERE author = ?";
    params = [author];
  }
  
  db.all(query, params, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json(rows);
  });
});

// Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(row);
  });
});

// Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  // Insert book into database
  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  stmt.run([title, author, year, isbn], function (err) {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.status(201).json({ id: this.lastID });
  });
});

// Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  // Check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Update book
    const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?');
    stmt.run([title, author, year, isbn, id], function (err) {
      if (err) {
        return res.status(500).json({ error: err.message });
      }
      res.json({ message: 'Book updated successfully' });
    });
  });
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  // Check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
  }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Delete book
    db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
      if (err) {
        return res.status(500).json({ error: err.message });
      }
      res.json({ message: 'Book deleted successfully' });
    });
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

module.exports = app;