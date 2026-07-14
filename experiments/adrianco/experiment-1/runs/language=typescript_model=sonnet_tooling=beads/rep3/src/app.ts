import express, { Request, Response, NextFunction } from 'express';
import Database from 'better-sqlite3';
import { createDb } from './db';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export function createApp(db: Database.Database) {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // POST /books
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'author is required' });
    }

    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(title.trim(), author.trim(), year ?? null, isbn ?? null);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    return res.status(201).json(book);
  });

  // GET /books
  app.get('/books', (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (author && typeof author === 'string') {
      books = db.prepare('SELECT * FROM books WHERE author LIKE ?').all(`%${author}%`) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books').all() as Book[];
    }
    return res.json(books);
  });

  // GET /books/:id
  app.get('/books/:id', (req: Request, res: Response) => {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.json(book);
  });

  // PUT /books/:id
  app.put('/books/:id', (req: Request, res: Response) => {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    const { title, author, year, isbn } = req.body;

    if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
      return res.status(400).json({ error: 'title must be a non-empty string' });
    }
    if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
      return res.status(400).json({ error: 'author must be a non-empty string' });
    }

    const updatedTitle = title !== undefined ? title.trim() : existing.title;
    const updatedAuthor = author !== undefined ? author.trim() : existing.author;
    const updatedYear = year !== undefined ? year : existing.year;
    const updatedIsbn = isbn !== undefined ? isbn : existing.isbn;

    db.prepare(
      `UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now') WHERE id = ?`
    ).run(updatedTitle, updatedAuthor, updatedYear, updatedIsbn, req.params.id);

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book;
    return res.json(book);
  });

  // DELETE /books/:id
  app.delete('/books/:id', (req: Request, res: Response) => {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
    return res.status(204).send();
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

// Only create the default app if not in test mode
let app: ReturnType<typeof createApp> | undefined;
if (require.main !== module) {
  const { db: defaultDb } = require('./db');
  app = createApp(defaultDb);
}

export { app };
