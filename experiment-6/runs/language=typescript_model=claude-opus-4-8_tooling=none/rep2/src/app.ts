import express, { Request, Response } from 'express';
import type { Database } from 'better-sqlite3';
import { Book } from './db';

interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

interface ValidatedBook {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/**
 * Validate and normalize a book payload.
 * Returns either the validated book or a list of error messages.
 */
function validateBook(body: BookInput): { value?: ValidatedBook; errors: string[] } {
  const errors: string[] = [];

  const title = typeof body.title === 'string' ? body.title.trim() : '';
  const author = typeof body.author === 'string' ? body.author.trim() : '';

  if (!title) errors.push('title is required and must be a non-empty string');
  if (!author) errors.push('author is required and must be a non-empty string');

  let year: number | null = null;
  if (body.year !== undefined && body.year !== null && body.year !== '') {
    const n = Number(body.year);
    if (!Number.isInteger(n)) {
      errors.push('year must be an integer');
    } else {
      year = n;
    }
  }

  let isbn: string | null = null;
  if (body.isbn !== undefined && body.isbn !== null && body.isbn !== '') {
    if (typeof body.isbn !== 'string') {
      errors.push('isbn must be a string');
    } else {
      isbn = body.isbn.trim();
    }
  }

  if (errors.length > 0) return { errors };
  return { value: { title, author, year, isbn }, errors };
}

export function createApp(db: Database) {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Create a book
  app.post('/books', (req: Request, res: Response) => {
    const { value, errors } = validateBook(req.body ?? {});
    if (!value) {
      return res.status(400).json({ errors });
    }
    const info = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(value.title, value.author, value.year, value.isbn);
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(info.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  // List all books, optional ?author= filter
  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author;
    let books: Book[];
    if (typeof author === 'string' && author.trim() !== '') {
      books = db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }
    res.status(200).json(books);
  });

  // Get a single book by ID
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(book);
  });

  // Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }
    const { value, errors } = validateBook(req.body ?? {});
    if (!value) {
      return res.status(400).json({ errors });
    }
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      value.title,
      value.author,
      value.year,
      value.isbn,
      id
    );
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    res.status(200).json(book);
  });

  // Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(204).send();
  });

  return app;
}
