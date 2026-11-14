import express, { Request, Response } from 'express';
import { db } from './database';
import { Book } from './types';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'OK' });
});

// POST /books — Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  if (!year || !isbn) {
    return res.status(400).json({ error: 'Year and ISBN are required' });
  }

  try {
    const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
    const result = stmt.run(title, author, year, isbn);
    const book: Book = { id: result.lastInsertRowid as number, title, author, year, isbn };
    res.status(201).json(book);
  } catch (err: any) {
    if (err.message?.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /books — List all books (support ?author= filter)
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;

  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    const books = stmt.all(author as string) as Book[];
    return res.json(books);
  }

  const books = db.prepare('SELECT * FROM books').all() as Book[];
  res.json(books);
});

// GET /books/:id — Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const book = stmt.get(id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

// PUT /books/:id — Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;

  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const updates: string[] = [];
  const values: any[] = [];

  if (title !== undefined) { updates.push('title = ?'); values.push(title); }
  if (author !== undefined) { updates.push('author = ?'); values.push(author); }
  if (year !== undefined) { updates.push('year = ?'); values.push(year); }
  if (isbn !== undefined) { updates.push('isbn = ?'); values.push(isbn); }

  if (updates.length === 0) {
    return res.status(400).json({ error: 'No valid fields to update' });
  }

  values.push(id);
  const stmt = db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`);
  stmt.run(...values);

  const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
  res.json(updated);
});

// DELETE /books/:id — Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.status(204).send();
});

let server: ReturnType<typeof app.listen> | undefined;

// Only start the server when run directly (not when imported by tests)
if (require.main === module) {
  server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export { app, server };
