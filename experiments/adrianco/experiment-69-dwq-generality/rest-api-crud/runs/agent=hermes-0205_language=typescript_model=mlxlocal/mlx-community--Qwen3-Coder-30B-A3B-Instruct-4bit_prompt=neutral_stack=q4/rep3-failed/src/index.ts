import express, { Request, Response } from 'express';
import sqlite3 from 'sqlite3';
import { Database } from 'sqlite3';

const app = express();
app.use(express.json());

// Initialize database
const db = new sqlite3.Database(':memory:'); // In-memory database for simplicity

// Create books table if it doesn't exist
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
  res.status(200).json({ status: 'OK' });
});

// Get all books (with optional author filter)
app.get('/books', (req: Request, res: Response) => {
  const author = req.query.author as string | undefined;
  let query = 'SELECT * FROM books';
  let params: any[] = [];

  if (author) {
    query += ' WHERE author = ?';
    params = [author];
  }

  db.all(query, params, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    res.json({ books: rows });
  });
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(row);
  });
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  // Insert book into database
  const sql = 'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)';
  db.run(sql, [title, author, year, isbn], function (this: any, err: any) {
    if (err) {
      return res.status(400).json({ error: err.message });
    }
    res.status(201).json({ id: this.lastID });
  });
});

// Update an existing book
app.put('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  const { title, author, year, isbn } = req.body;

  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  // Check if book exists
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (!row) {
      return res.status(404).json({ error: 'Book not found' });
    }

    // Update book
    const sql = 'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?";
    db.run(sql, [title, author, year, isbn, id], function (this: any, err: any) {
      if (err) {
        return res.status(400).json({ error: err.message });
      }
      res.json({ message: 'Book updated successfully' });
    });
  });
});

// Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  db.run('DELETE FROM books WHERE id = ?', [id], function (this: any, err: any) {
    if (err) {
      return res.status(500).json({ error: err.message });
    }
    if (this.rowsAffected === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json({ message: 'Book deleted successfully' });
  });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

export default app;