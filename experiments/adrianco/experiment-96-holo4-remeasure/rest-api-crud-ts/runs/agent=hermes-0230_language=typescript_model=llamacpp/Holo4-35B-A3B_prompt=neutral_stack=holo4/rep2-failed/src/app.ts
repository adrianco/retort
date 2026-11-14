import express, { Request, Response } from 'express';
import { db } from './database';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year || null, isbn || null);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(book);
});

// List all books (support ?author= filter)
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;

  if (author) {
    const books = db.prepare('SELECT * FROM books WHERE author = ?').all(author);
    return res.json(books);
  }

  const books = db.prepare('SELECT * FROM books').all();
  res.json(books);
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

// Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const updateFields: string[] = [];
  const values: any[] = [];

  if (title !== undefined) {
    updateFields.push('title = ?');
    values.push(title);
  }
  if (author !== undefined) {
    updateFields.push('author = ?');
    values.push(author);
  }
  if (year !== undefined) {
    updateFields.push('year = ?');
    values.push(year);
  }
  if (isbn !== undefined) {
    updateFields.push('isbn = ?');
    values.push(isbn);
  }

  if (updateFields.length === 0) {
    return res.status(400).json({ error: 'No fields to update' });
  }

  values.push(id);
  db.prepare(`UPDATE books SET ${updateFields.join(', ')} WHERE id = ?`).run(...values);

  const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(updated);
});

// Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.status(204).send();
});

export { app };
