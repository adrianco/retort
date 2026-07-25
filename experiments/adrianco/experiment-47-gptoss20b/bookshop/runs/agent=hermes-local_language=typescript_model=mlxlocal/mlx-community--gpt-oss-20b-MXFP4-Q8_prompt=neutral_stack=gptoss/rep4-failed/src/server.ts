import express, { Request, Response } from 'express';
import bodyParser from 'body-parser';
import { db } from './database';

const app = express();
app.use(bodyParser.json());

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Create book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const info = stmt.run(title, author, year ?? null, isbn ?? null);
  const book = { id: info.lastInsertRowid, title, author, year, isbn };
  res.status(201).json(book);
});

// List books with optional author filter
app.get('/books', (req, res) => {
  const { author } = req.query;
  let stmt;
  if (author) {
    stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    const books = stmt.all(author as string);
    res.json(books);
  } else {
    stmt = db.prepare('SELECT * FROM books');
    const books = stmt.all();
    res.json(books);
  }
});

// Get single book
app.get('/books/:id', (req, res) => {
  const { id } = req.params;
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const book = stmt.get(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(book);
});

// Update book
app.put('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;
  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const stmt = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?');
  const info = stmt.run(title, author, year ?? null, isbn ?? null, id);
  if (info.changes === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }
  const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
  res.json(updated);
});

// Delete book
app.delete('/books/:id', (req, res) => {
  const { id } = req.params;
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const info = stmt.run(id);
  if (info.changes === 0) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.status(204).send();
});

export default app;
