import express, { Request, Response } from 'express';
import { initDatabase, getDb } from './database';
import type { Book } from './types';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books - Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  const db = getDb();
  const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run(title, author, year || null, isbn || null);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
  res.status(201).json(book);
});

// GET /books - List all books with optional ?author= filter
app.get('/books', (req: Request, res: Response) => {
  const db = getDb();
  const author = req.query.author as string | undefined;

  let books;
  if (author) {
    books = db.prepare('SELECT * FROM books WHERE author = ?').all(author) as Book[];
  } else {
    books = db.prepare('SELECT * FROM books').all() as Book[];
  }

  res.status(200).json(books);
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const db = getDb();
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.status(200).json(book);
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const db = getDb();
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(title, author, year || null, isbn || null, req.params.id);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book;
  res.status(200).json(book);
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const db = getDb();
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.status(200).json({ message: 'Book deleted successfully' });
});

// Initialize database and start server
initDatabase();

const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export { app, server };
