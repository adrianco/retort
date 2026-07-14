const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
let db;

function initDB() {
  return new Promise((resolve, reject) => {
    // Open or create database
    db = new sqlite3.Database('./books.db', (err) => {
      if (err) {
        console.error('Failed to connect to database:', err);
        reject(err);
      } else {
        console.log('Connected to database');
        
        // Create books table if it doesn't exist
        db.serialize(() => {
          db.run(`
            CREATE TABLE IF NOT EXISTS books (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              author TEXT NOT NULL,
              year INTEGER,
              isbn TEXT
            )
          `, (err) => {
            if (err) {
              console.error('Failed to create books table:', err);
              reject(err);
            } else {
              console.log('Books table ready');
              resolve();
            }
          });
        });
      }
    });
  });
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
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
      console.error('Error fetching books:', err);
      return res.status(500).json({ error: 'Failed to fetch books' });
    }
    res.status(200).json(rows);
  });
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Error fetching book:', err);
      return res.status(500).json({ error: 'Failed to fetch book' });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(row);
  });
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
  
  db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [title, author, year, isbn],
    function(err) {
      if (err) {
        console.error('Error creating book:', err);
        return res.status(500).json({ error: 'Failed to create book' });
      }
      
      const book = {
        id: this.lastID,
        title,
        author,
        year,
        isbn
      };
      
      res.status(201).json(book);
    }
  );
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const { title, author, year, isbn } = req.body;
  
  // Validation
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Error checking book:', err);
      return res.status(500).json({ error: 'Failed to check book' });
    }
    
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year, isbn, id],
      function(err) {
        if (err) {
          console.error('Error updating book:', err);
          return res.status(500).json({ error: 'Failed to update book' });
        }
        
        const updatedBook = {
          id,
          title,
          author,
          year,
          isbn
        };
        
        res.status(200).json(updatedBook);
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
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Error checking book:', err);
      return res.status(500).json({ error: 'Failed to check book' });
    }
    
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    db.run('DELETE FROM books WHERE id = ?', [id], function(err) {
      if (err) {
        console.error('Error deleting book:', err);
        return res.status(500).json({ error: 'Failed to delete book' });
      }
      
      res.status(200).json({ message: 'Book deleted successfully' });
    });
  });
});

// Error handling middleware
app.use((err, req, res) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Start server
async function startServer() {
  try {
    await initDB();
    app.listen(PORT, () => {
      console.log(`Server is running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

module.exports = app;