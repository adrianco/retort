const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database with error handling
let db;
try {
  const dbPath = path.join(__dirname, '../books.db');
  db = new sqlite3.Database(dbPath);
  
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
        console.error('Error creating table:', err);
      }
    });
  });
} catch (error) {
  console.error('Failed to initialize database:', error);
  process.exit(1);
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// POST /books - Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: 'Title and author are required'
    });
  }
  
  const query = `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`;
  const params = [title, author, year, isbn];
  
  db.run(query, params, function(err) {
    if (err) {
      if (err.message.includes('UNIQUE')) {
        return res.status(400).json({
          error: 'ISBN must be unique'
        });
      }
      console.error('Database error on insert:', err);
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
      console.error('Database error on select:', err);
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
  const query = 'SELECT * FROM books WHERE id = ?';
  
  db.get(query, [id], (err, row) => {
    if (err) {
      console.error('Database error on select by id:', err);
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
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: 'Title and author are required'
    });
  }
  
  const query = `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`;
  const params = [title, author, year, isbn, id];
  
  db.run(query, params, function(err) {
    if (err) {
      if (err.message.includes('UNIQUE')) {
        return res.status(400).json({
          error: 'ISBN must be unique'
        });
      }
      console.error('Database error on update:', err);
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

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const id = req.params.id;
  const query = 'DELETE FROM books WHERE id = ?';
  
  db.run(query, [id], function(err) {
    if (err) {
      console.error('Database error on delete:', err);
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

// Handle 404 for undefined routes
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found'
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Something went wrong!'
  });
});

// Export for testing
module.exports = {
  app,
  db
};

// Start server only if run directly
if (require.main === module) {
  app.listen(port, () => {
    console.log(`Book API server listening at http://localhost:${port}`);
  });
}