const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');

// Initialize database with proper error handling
let db;

function initDB() {
  return new Promise((resolve, reject) => {
    try {
      // Create directory if it doesn't exist
      const dbPath = './books.db';
      
      // Ensure the database file exists
      if (!fs.existsSync(dbPath)) {
        fs.writeFileSync(dbPath, '');
      }
      
      db = new sqlite3.Database(dbPath, (err) => {
        if (err) {
          console.error('Failed to connect to database', err);
          reject(err);
        } else {
          // Create table if it doesn't exist
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
                console.error('Failed to create table', err);
                reject(err);
              } else {
                resolve();
              }
            });
          });
        }
      });
    } catch (error) {
      reject(error);
    }
  });
}

// Create Express app
const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// GET /books - List all books with optional author filter
app.get('/books', (req, res) => {
  const author = req.query.author;
  
  if (author) {
    db.all('SELECT * FROM books WHERE author = ?', [author], (err, rows) => {
      if (err) {
        console.error('Database error in GET /books:', err);
        res.status(500).json({ error: 'Internal server error' });
      } else {
        res.status(200).json(rows);
      }
    });
  } else {
    db.all('SELECT * FROM books', (err, rows) => {
      if (err) {
        console.error('Database error in GET /books:', err);
        res.status(500).json({ error: 'Internal server error' });
      } else {
        res.status(200).json(rows);
      }
    });
  }
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Database error in GET /books/:id:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else if (!row) {
      res.status(404).json({ error: 'Book not found' });
    } else {
      res.status(200).json(row);
    }
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
  
  db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [title, author, year, isbn],
    function(err) {
      if (err) {
        console.error('Database error in POST /books:', err);
        res.status(500).json({ error: 'Internal server error' });
      } else {
        db.get('SELECT * FROM books WHERE id = ?', [this.lastID], (err2, row) => {
          if (err2) {
            console.error('Database error in POST /books (fetch):', err2);
            res.status(500).json({ error: 'Internal server error' });
          } else {
            res.status(201).json(row);
          }
        });
      }
    }
  );
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      console.error('Database error in PUT /books/:id:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else if (!row) {
      res.status(404).json({ error: 'Book not found' });
    } else {
      db.run(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        [title, author, year, isbn, id],
        function(err) {
          if (err) {
            console.error('Database error in PUT /books/:id:', err);
            res.status(500).json({ error: 'Internal server error' });
          } else {
            db.get('SELECT * FROM books WHERE id = ?', [id], (err2, row2) => {
              if (err2) {
                console.error('Database error in PUT /books/:id (fetch):', err2);
                res.status(500).json({ error: 'Internal server error' });
              } else {
                res.status(200).json(row2);
              }
            });
          }
        }
      );
    }
  });
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  db.run('DELETE FROM books WHERE id = ?', [id], function(err) {
    if (err) {
      console.error('Database error in DELETE /books/:id:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else {
      if (this.changes === 0) {
        res.status(404).json({ error: 'Book not found' });
      } else {
        res.status(200).json({ message: 'Book deleted successfully' });
      }
    }
  });
});

// Export for testing if needed
module.exports = { app, initDB };

// Start server only if not required as a module (i.e., run directly)
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  
  app.listen(PORT, async () => {
    try {
      await initDB();
      console.log(`Book API server running on port ${PORT}`);
    } catch (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
  });
}