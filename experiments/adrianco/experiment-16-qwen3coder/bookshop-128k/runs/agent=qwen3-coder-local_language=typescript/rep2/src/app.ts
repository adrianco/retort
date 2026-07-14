import express from 'express';
import sqlite3 from 'sqlite3';

// Initialize Express app
const app = express();
const port = 3000;

// Middleware
app.use(express.json());

// Initialize database
let db: any;

async function initDB(): Promise<void> {
  db = new sqlite3.Database('./books.db');
  
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT UNIQUE
      )
    `);
  });
}

// Health check endpoint
app.get('/health', (req: any, res: any) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// GET /books - List all books with optional author filter
app.get('/books', (req: any, res: any) => {
  try {
    const author = req.query.author;
    
    let query = 'SELECT * FROM books';
    let params: any[] = [];
    
    if (author) {
      query += ' WHERE author = ?';
      params = [author];
    }
    
    db.all(query, params, (err: any, rows: any[]) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to fetch books' });
      }
      res.status(200).json(rows);
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req: any, res: any) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    db.get('SELECT * FROM books WHERE id = ?', [id], (err: any, row: any) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to fetch book' });
      }
      
      if (!row) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      res.status(200).json(row);
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// POST /books - Create a new book
app.post('/books', (req: any, res: any) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required' 
      });
    }
    
    db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn],
      function(err: any) {
        if (err) {
          if (err.message.includes('UNIQUE constraint failed')) {
            return res.status(409).json({ error: 'Book with this ISBN already exists' });
          }
          return res.status(500).json({ error: 'Failed to create book' });
        }
        
        db.get('SELECT * FROM books WHERE id = ?', [this.lastID], (err: any, row: any) => {
          if (err) {
            return res.status(500).json({ error: 'Failed to fetch created book' });
          }
          res.status(201).json(row);
        });
      }
    );
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req: any, res: any) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required' 
      });
    }
    
    db.get('SELECT * FROM books WHERE id = ?', [id], (err: any, row: any) => {
      if (err) {
        return res.status(500).json({ error: 'Failed to check book existence' });
      }
      
      if (!row) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      db.run(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        [title, author, year, isbn, id],
        function(err: any) {
          if (err) {
            if (err.message.includes('UNIQUE constraint failed')) {
              return res.status(409).json({ error: 'Book with this ISBN already exists' });
            }
            return res.status(500).json({ error: 'Failed to update book' });
          }
          
          db.get('SELECT * FROM books WHERE id = ?', [id], (err: any, updatedRow: any) => {
            if (err) {
              return res.status(500).json({ error: 'Failed to fetch updated book' });
            }
            res.status(200).json(updatedRow);
          });
        }
      );
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req: any, res: any) => {
  try {
    const id = parseInt(req.params.id);
    
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    db.run('DELETE FROM books WHERE id = ?', [id], function(err: any) {
      if (err) {
        return res.status(500).json({ error: 'Failed to delete book' });
      }
      
      if (this.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      res.status(200).json({ message: 'Book deleted successfully' });
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// Error handling middleware
app.use((err: any, req: any, res: any, next: any) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use((req: any, res: any) => {
  res.status(404).json({ error: 'Route not found' });
});

// Start server
async function startServer(): Promise<void> {
  try {
    await initDB();
    app.listen(port, () => {
      console.log(`Server is running on http://localhost:${port}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Export for testing
export { app, startServer };

// Start server if this file is run directly
if (require.main === module) {
  startServer();
}