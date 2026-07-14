import express from 'express';
import sqlite3 from 'sqlite3';

// Initialize Express app
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
let db: any;

function initDB() {
  db = new sqlite3.Database('./books.db', (err: any) => {
    if (err) {
      console.error('Error opening database:', err.message);
    } else {
      console.log('Connected to the books database.');
      db.run(`
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER,
          isbn TEXT
        )
      `);
    }
  });
}

// Health check endpoint
app.get('/health', (req: any, res: any) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// POST /books - Create a new book
app.post('/books', (req: any, res: any) => {
  const { title, author, year, isbn } = req.body;

  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }

  db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [title, author, year || null, isbn || null],
    function(err: any) {
      if (err) {
        return res.status(500).json({ error: 'Failed to create book' });
      }
      
      const book = {
        id: this.lastID,
        title,
        author,
        year: year || null,
        isbn: isbn || null
      };
      
      res.status(201).json(book);
    }
  );
});

// GET /books - List all books with optional author filter
app.get('/books', (req: any, res: any) => {
  const { author } = req.query;
  
  let query = 'SELECT * FROM books';
  let params: any[] = [];
  
  if (author) {
    query += ' WHERE author LIKE ?';
    params = [`%${author}%`];
  }
  
  db.all(query, params, (err: any, rows: any) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to fetch books' });
    }
    res.json(rows);
  });
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req: any, res: any) => {
  const { id } = req.params;
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err: any, row: any) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to fetch book' });
    }
    
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json(row);
  });
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req: any, res: any) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
    });
  }
  
  db.run(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
    [title, author, year || null, isbn || null, id],
    function(err: any) {
      if (err) {
        return res.status(500).json({ error: 'Failed to update book' });
      }
      
      if (this.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }
      
      const updatedBook = {
        id: parseInt(id),
        title,
        author,
        year: year || null,
        isbn: isbn || null
      };
      
      res.json(updatedBook);
    }
  );
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req: any, res: any) => {
  const { id } = req.params;
  
  db.run('DELETE FROM books WHERE id = ?', [id], function(err: any) {
    if (err) {
      return res.status(500).json({ error: 'Failed to delete book' });
    }
    
    if (this.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json({ message: 'Book deleted successfully' });
  });
});

// Start server
initDB();
app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
