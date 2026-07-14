import express, { Request, Response, NextFunction } from 'express';
import type Database from 'better-sqlite3';
import { Book, createDb } from './db';

interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

function validateBookInput(body: BookInput): { ok: true; data: { title: string; author: string; year: number | null; isbn: string | null } } | { ok: false; error: string } {
  const { title, author, year, isbn } = body;

  if (typeof title !== 'string' || title.trim() === '') {
    return { ok: false, error: 'title is required and must be a non-empty string' };
  }
  if (typeof author !== 'string' || author.trim() === '') {
    return { ok: false, error: 'author is required and must be a non-empty string' };
  }

  let yearValue: number | null = null;
  if (year !== undefined && year !== null) {
    if (typeof year !== 'number' || !Number.isInteger(year)) {
      return { ok: false, error: 'year must be an integer' };
    }
    yearValue = year;
  }

  let isbnValue: string | null = null;
  if (isbn !== undefined && isbn !== null) {
    if (typeof isbn !== 'string') {
      return { ok: false, error: 'isbn must be a string' };
    }
    isbnValue = isbn;
  }

  return {
    ok: true,
    data: {
      title: title.trim(),
      author: author.trim(),
      year: yearValue,
      isbn: isbnValue,
    },
  };
}

export function createApp(db: Database.Database = createDb()) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const validation = validateBookInput(req.body ?? {});
    if (!validation.ok) {
      return res.status(400).json({ error: validation.error });
    }
    const { title, author, year, isbn } = validation.data;
    const result = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title, author, year, isbn);
    const book = db
      .prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?')
      .get(result.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author;
    let rows: Book[];
    if (typeof author === 'string' && author.trim() !== '') {
      rows = db
        .prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    } else {
      rows = db
        .prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id')
        .all() as Book[];
    }
    res.status(200).json(rows);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const book = db
      .prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?')
      .get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const existing = db.prepare('SELECT id FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }
    const validation = validateBookInput(req.body ?? {});
    if (!validation.ok) {
      return res.status(400).json({ error: validation.error });
    }
    const { title, author, year, isbn } = validation.data;
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      title,
      author,
      year,
      isbn,
      id,
    );
    const updated = db
      .prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?')
      .get(id) as Book;
    res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError) {
      return res.status(400).json({ error: 'invalid JSON body' });
    }
    res.status(500).json({ error: 'internal server error' });
  });

  return app;
}
