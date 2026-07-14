import express, { Request, Response, NextFunction } from 'express';
import { getDb } from './db';

export function createApp() {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // POST /books — Create a new book
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      res.status(400).json({ error: 'title is required' });
      return;
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      res.status(400).json({ error: 'author is required' });
      return;
    }

    const db = getDb();
    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(title.trim(), author.trim(), year ?? null, isbn ?? null);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(book);
  });

  // GET /books — List all books (with optional ?author= filter)
  app.get('/books', (req: Request, res: Response) => {
    const db = getDb();
    const { author } = req.query;

    let books;
    if (author && typeof author === 'string') {
      books = db.prepare('SELECT * FROM books WHERE author LIKE ? ORDER BY id').all(`%${author}%`);
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY id').all();
    }
    res.json(books);
  });

  // GET /books/:id — Get a single book
  app.get('/books/:id', (req: Request, res: Response) => {
    const db = getDb();
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    res.json(book);
  });

  // PUT /books/:id — Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const db = getDb();
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!existing) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    const { title, author, year, isbn } = req.body;

    if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
      res.status(400).json({ error: 'title cannot be empty' });
      return;
    }
    if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
      res.status(400).json({ error: 'author cannot be empty' });
      return;
    }

    const current = existing as Record<string, unknown>;
    const newTitle = title !== undefined ? title.trim() : current.title;
    const newAuthor = author !== undefined ? author.trim() : current.author;
    const newYear = year !== undefined ? year : current.year;
    const newIsbn = isbn !== undefined ? isbn : current.isbn;

    db.prepare(
      `UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now') WHERE id = ?`
    ).run(newTitle, newAuthor, newYear, newIsbn, req.params.id);

    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    res.json(updated);
  });

  // DELETE /books/:id — Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const db = getDb();
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!existing) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
    res.status(204).send();
  });

  // 404 handler
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: 'Not found' });
  });

  // Error handler
  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
