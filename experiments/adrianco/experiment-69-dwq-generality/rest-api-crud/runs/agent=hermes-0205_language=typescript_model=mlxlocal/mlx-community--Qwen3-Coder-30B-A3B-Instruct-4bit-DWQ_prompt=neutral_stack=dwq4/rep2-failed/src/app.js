const express = require('express');
const sqlite3 = require('sqlite3').verbose();

// Initialize SQLite database
let db;

function initDB() {
  return new Promise((resolve, reject) => {
    db = new sqlite3.Database('./books.db', (err) => {
      if (err) {
        reject(err);
      } else {
        // Create books table if it doesn't exist
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
            reject(err);
          } else {
            resolve(undefined);
          }
        });
      }
    });
  });
}

// Express app setup
const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// Create a new book
app.post('/books', (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;

    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({
        error: 'Title and author are required fields'
      });
    }

    const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
    stmt.run([title, author, year || null, isbn || null], function (err) {
      if (err) {
        res.status(500).json({ error: 'Failed to create book' });
      } else {
        const newBook = {
          id: this.lastID,
          title,
          author,
          year,
          isbn
        };
        res.status(201).json(newBook);
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Get all books with optional author filter
app.get('/books', (req, res) => {
  try {
    const { author } = req.query;
    
    let query = 'SELECT * FROM books';
    let params = [];
    
    if (author) {
      query = 'SELECT * FROM books WHERE author LIKE ?';
      params = [`%${author}%`];
    }

    db.all(query, params, (err, rows) => {
      if (err) {
        res.status(500).json({ error: 'Failed to fetch books' });
      } else {
        res.status(200).json(rows);
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get a single book by ID
app.get('/books/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) {
        res.status(500).json({ error: 'Failed to fetch book' });
      } else if (!row) {
        res.status(404).json({ error: 'Book not found' });
      } else {
        res.status(200).json(row);
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// Update a book
app.put('/books/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const { title, author, year, isbn } = req.body;

    // Check if book exists
    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) {
        res.status(500).json({ error: 'Failed to check book existence' });
      } else if (!row) {
        res.status(404).json({ error: 'Book not found' });
      } else {
        // Validate required fields
        if (!title || !author) {
          return res.status(400).json({
            error: 'Title and author are required fields'
          });
        }

        const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?');
        stmt.run([title, author, year || null, isbn || null, id], function (err) {
          if (err) {
            res.status(500).json({ error: 'Failed to update book' });
          } else {
            const updatedBook = {
              id,
              title,
              author,
              year,
              isbn
            };
            res.status(200).json(updatedBook);
          }
        });
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
      if (err) {
        res.status(500).json({ error: 'Failed to delete book' });
      } else {
        if (this.changes === 0) {
          res.status(404).json({ error: 'Book not found' });
        } else {
          res.status(200).json({ message: 'Book deleted successfully' });
        }
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// Start server
initDB().then(() => {
  app.listen(PORT, () => {
    console.log(`Book API server is running on port ${PORT}`);
  });
}).catch(error => {
  console.error('Failed to initialize database:', error);
});

module.exports = { app, db };