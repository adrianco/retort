const express = require('express');
const sqlite3 = require('sqlite3');
const fs = require('fs');

// Initialize database
let db;

function initDB() {
  // Check if database file exists, create it if not
  const dbExists = fs.existsSync('./books.db');
  
  db = new sqlite3.Database('./books.db', (err) => {
    if (err) {
      console.error('Failed to connect to database:', err.message);
    } else {
      console.log('Connected to SQLite database');
    }
  });

  // Create books table if it doesn't exist
  if (!dbExists) {
    db.serialize(() => {
      db.run(`
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER,
          isbn TEXT
        )
      `);
    });
  }
}

// Initialize the application
const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy' });
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

  db.serialize(() => {
    db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year || null, isbn || null],
      function (err) {
        if (err) {
          return res.status(500).json({ error: 'Failed to create book' });
        }
        
        db.get('SELECT * FROM books WHERE id = ?', [this.lastID], (err, row) => {
          if (err) {
            return res.status(500).json({ error: 'Failed to fetch created book' });
          }
          res.status(201).json(row);
        });
      }
    );
  });
});

// GET /books - List all books (with optional author filter)
app.get('/books', (req, res) => {
  const { author } = req.query;
  
  db.serialize(() => {
    let query = 'SELECT * FROM books';
    let params = [];
    
    if (author) {
      query = 'SELECT * FROM books WHERE author = ?';
      params = [author];
    }
    
    db.all(query, params, (err, rows) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to fetch books' });
      }
      res.status(200).json(rows);
    });
  });
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.serialize(() => {
    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to fetch book' });
      }
      
      if (!row) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      res.status(200).json(row);
    });
  });
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const { title, author, year, isbn } = req.body;
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  db.serialize(() => {
    db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year || null, isbn || null, id],
      function (err) {
        if (err) {
          return res.status(500).json({ error: 'Failed to update book' });
        }
        
        if (this.changes === 0) {
          return res.status(404).json({ error: 'Book not found' });
        }
        
        db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
          if (err) {
            return res.status(500).json({ error: 'Failed to fetch updated book' });
          }
          res.status(200).json(row);
        });
      }
    );
  });
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.serialize(() => {
    db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
      if (err) {
        return res.status(500).json({ error: 'Failed to delete book' });
      }
      
      if (this.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      res.status(200).json({ message: 'Book deleted successfully' });
    });
  });
});

// Start server
const PORT = process.env.PORT || 3000;

initDB();
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

module.exports = { app, initDB };