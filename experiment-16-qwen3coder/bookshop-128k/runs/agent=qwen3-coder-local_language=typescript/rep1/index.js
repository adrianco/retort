const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
const dbPath = path.join(__dirname, 'books.db');
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Failed to connect to database:', err);
    process.exit(1);
  }
});

// Create books table if it doesn't exist
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
  )`, (err) => {
    if (err) {
      console.error('Failed to create books table:', err);
      process.exit(1);
    }
  });
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

// Graceful shutdown
process.on('SIGINT', () => {
  db.close((err) => {
    if (err) {
      console.error('Error closing database:', err);
    }
    console.log('Database connection closed.');
    process.exit(0);
  });
});

// Start the server
app.listen(port, () => {
  console.log(`Book API server listening at http://localhost:${port}`);
});

module.exports = app;