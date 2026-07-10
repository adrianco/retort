const express = require('express');
const { Database } = require('sqlite3');

const app = express();

// Middleware
app.use(express.json());

// Initialize database
const db = new Database(':memory:'); // Using in-memory DB for simplicity

// Create books table
db.serialize(() => {
  db.run(`CREATE TABLE books (
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
      error: 'Title and author are required'
    });
  }
  
  const query = `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`;
  const params = [title, author, year || null, isbn || null];
  
  db.run(query, params, function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        return res.status(400).json({
          error: 'ISBN already exists'
        });
      }
      return res.status(500).json({
        error: 'Failed to create book'
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
    query += ' WHERE author = ?';
    params = [author];
  }
  
  db.all(query, params, (err, rows) => {
    if (err) {
      return res.status(500).json({
        error: 'Failed to fetch books'
      });
    }
    
    res.json(rows);
  });
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = req.params.id;
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({
        error: 'Failed to fetch book'
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
      error: 'Title and author are required'
    });
  }
  
  // Check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({
        error: 'Failed to update book'
      });
    }
    
    if (!row) {
      return res.status(404).json({
        error: 'Book not found'
      });
    }
    
    const query = `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`;
    const params = [title, author, year || null, isbn || null, id];
    
    db.run(query, params, function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          return res.status(400).json({
            error: 'ISBN already exists'
          });
        }
        return res.status(500).json({
          error: 'Failed to update book'
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
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const id = req.params.id;
  
  db.run('DELETE FROM books WHERE id = ?', [id], function(err) {
    if (err) {
      return res.status(500).json({
        error: 'Failed to delete book'
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

// Start server only if not being required by test
if (require.main === module) {
  const PORT = process.env.PORT || 3001;
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}

module.exports = app;