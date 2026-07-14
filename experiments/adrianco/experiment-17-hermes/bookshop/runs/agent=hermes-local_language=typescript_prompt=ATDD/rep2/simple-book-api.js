const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
const dbPath = path.join(__dirname, 'books.db');
const db = new sqlite3.Database(dbPath);

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
  `);
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: 'Title and author are required'
    });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  stmt.run([title, author, year, isbn], function(err) {
    if (err) {
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    res.status(201).json({
      id: this.lastID,
      title,
      author,
      year,
      isbn
    });
  });
  stmt.finalize();
});

// Get all books with optional author filter
app.get('/books', (req, res) => {
  const author = req.query.author;
  let sql = 'SELECT * FROM books';
  const params = [];
  
  if (author) {
    sql += ' WHERE author = ?';
    params.push(author);
  }
  
  db.all(sql, params, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: 'Internal server error' });
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
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json(row);
  });
});

// Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const { title, author, year, isbn } = req.body;
  
  // Check if the book exists first
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }

    // Build dynamic update query
    const updates = [];
    const values = [];
    
    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    
    if (author !== undefined) {
      updates.push('author = ?');
      values.push(author);
    }
    
    if (year !== undefined) {
      updates.push('year = ?');
      values.push(year);
    }
    
    if (isbn !== undefined) {
      updates.push('isbn = ?');
      values.push(isbn);
    }
    
    if (updates.length === 0) {
      // If no fields are provided, return the existing book
      return res.json(row);
    }
    
    values.push(id); // Add id to the end for WHERE clause
    
    const sql = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;
    
    db.run(sql, values, function(err) {
      if (err) {
        return res.status(500).json({ error: 'Internal server error' });
      }
      
      // Get the updated book
      db.get('SELECT * FROM books WHERE id = ?', [id], (err, updatedRow) => {
        if (err) {
          return res.status(500).json({ error: 'Internal server error' });
        }
        res.json(updatedRow);
      });
    });
  });
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  db.run('DELETE FROM books WHERE id = ?', [id], function(err) {
    if (err) {
      return res.status(500).json({ error: 'Internal server error' });
    }
    
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(204).send();
  });
});

// Handle 404 for undefined routes
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

module.exports = app;
