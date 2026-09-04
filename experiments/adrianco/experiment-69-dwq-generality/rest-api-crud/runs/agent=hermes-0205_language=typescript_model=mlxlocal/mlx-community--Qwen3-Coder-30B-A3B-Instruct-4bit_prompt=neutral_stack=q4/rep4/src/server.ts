import express, { Application, Request, Response } from 'express';
import sqlite3 from 'sqlite3';
import { Database } from 'sqlite3';

const app: Application = express();
const port: number = 3000;

// Middleware to parse JSON
app.use(express.json());

// Create or open database
const db = new sqlite3.Database(':memory:'); // Using in-memory database for simplicity

// Create books table
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
  )`);
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', message: 'Book API service is running' });
});

// Get all books with optional author filter
app.get('/books', (req: Request, res: Response) => {
  const author = req.query.author as string;
  
  let query = 'SELECT * FROM books';
  let params: any[] = [];

  if (author) {
    query += ' WHERE author = ?";
    params = [author];
  }

  db.all(query, params, (err: Error | null, rows: any[]) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.status(200).json({ books: rows });
  });
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  
  db.get('SELECT * FROM books WHERE id = ?', [id], (err: Error | null, row: any) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json({ book: row });
  });
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  // Insert the book into the database
  const insertQuery = 'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)';
  db.run(insertQuery, [title, author, year, isbn], function (this: any, err: Error | null) {
    if (err) {
      if (err.message.includes('UNIQUE constraint')) {
        return res.status(400).json({ error: 'ISBN already exists' });
      }
      return res.status(500).json({ error: err.message });
    }
    res.status(201).json({ book: { id: this.lastID, title, author, year, isbn } });
  });
});

// Update a book by ID
app.put('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  const { title, author, year, isbn } = req.body;
  
  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }
  
  // Check if book exists
  db.get('SELECT id FROM books WHERE id = ?', [id], (err: Error | null, row: any) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Update the book
    const updateQuery = 'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
    db.run(updateQuery, [title, author, year, isbn, id], function (this: any, err: Error | null) {
      if (err) {
        if (err.message.includes('UNIQUE constraint')) {
          return res.status(400).json({ error: 'ISBN already exists' });
        }
        return res.status(500).json({ error: err.message });
      }
      res.status(200).json({ book: { id, title, author, year, isbn } });
    });
  });
});

// Delete a book by ID
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  
  // Check if book exists
  db.get('SELECT id FROM books WHERE id = ?', [id], (err: Error | null, row: any) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Delete the book
    const deleteQuery = 'DELETE FROM books WHERE id = ?";
    db.run(deleteQuery, [id], function (this: any, err: Error | null) {
      if (err) {
        return res.status(500).json({ error: err.message });
      }
      res.status(200).json({ message: 'Book deleted successfully' });
    });
  });
});

// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});

export default app;