import express, { Request, Response } from 'express';
import sqlite3 from 'sqlite3';
import { json } from 'body-parser';

const app = express();
app.use(json());

// Initialize in-memory SQLite database
const db = new sqlite3.Database(':memory:');
// Create books table
const createTable = `CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT
)`;
// Use serialize to ensure table creation before any queries
db.serialize(() => {
  db.run(createTable);
});

// Helper to validate book data
function validateBook(body: any): string[] {
  const errors: string[] = [];
  if (!body.title) errors.push('title is required');
  if (!body.author) errors.push('author is required');
  return errors;
}

// POST /books
app.post('/books', (req: Request, res: Response) => {
  const errors = validateBook(req.body);
  if (errors.length) {
    return res.status(400).json({ errors });
  }
  const { title, author, year, isbn } = req.body;
  const stmt = `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`;
  db.run(stmt, [title, author, year || null, isbn || null], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    const id = this.lastID;
    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json(row);
    });
  });
});

// GET /books with optional author filter
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;
  if (author) {
    db.all('SELECT * FROM books WHERE author = ?', [author as string], (err, rows) => {
      if (err) return res.status(500).json({ error: err.message });
      res.json(rows);
    });
  } else {
    db.all('SELECT * FROM books', [], (err, rows) => {
      if (err) return res.status(500).json({ error: err.message });
      res.json(rows);
    });
  }
});

// GET /books/:id
app.get('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Not found' });
    res.json(row);
  });
});

// PUT /books/:id
app.put('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Not found' });
    const errors = validateBook(req.body);
    if (errors.length) return res.status(400).json({ errors });
    const { title, author, year, isbn } = req.body;
    const stmt = `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`;
    db.run(stmt, [title, author, year || null, isbn || null, id], function (err) {
      if (err) return res.status(500).json({ error: err.message });
      db.get('SELECT * FROM books WHERE id = ?', [id], (err, updated) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(updated);
      });
    });
  });
});

// DELETE /books/:id
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = req.params.id;
  db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Not found' });
    db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(204).send();
    });
  });
});

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok' });
});

export const server = app;

if (require.main === module) {
  const port = process.env.PORT ?? 3000;
  app.listen(port, () => console.log(`Server listening on ${port}`));
}
