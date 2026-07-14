import express, { Request, Response, NextFunction } from 'express';
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

function validateBook(body: BookInput): { ok: true; value: ValidatedBook } | { ok: false; error: string } {
  if (typeof body.title !== 'string' || body.title.trim() === '') {
    return { ok: false, error: 'title is required and must be a non-empty string' };
  }
  if (typeof body.author !== 'string' || body.author.trim() === '') {
    return { ok: false, error: 'author is required and must be a non-empty string' };
  }
  let year: number | null = null;
  if (body.year !== undefined && body.year !== null) {
    if (typeof body.year !== 'number' || !Number.isInteger(body.year)) {
      return { ok: false, error: 'year must be an integer' };
    }
    year = body.year;
  }
  let isbn: string | null = null;
  if (body.isbn !== undefined && body.isbn !== null) {
    if (typeof body.isbn !== 'string') {
      return { ok: false, error: 'isbn must be a string' };
    }
    isbn = body.isbn;
  }
  return {
    ok: true,
    value: {
      title: body.title.trim(),
      author: body.author.trim(),
      year,
      isbn,
    },
  };
}

function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

export function createApp(db: Database): express.Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const result = validateBook(req.body ?? {});
    if (!result.ok) {
      return res.status(400).json({ error: result.error });
    }
    const { title, author, year, isbn } = result.value;
    const info = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title, author, year, isbn);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(info.lastInsertRowid) as Book;
    return res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author;
    let rows: Book[];
    if (typeof author === 'string' && author.length > 0) {
      rows = db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    } else {
      rows = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }
    return res.status(200).json(rows);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    return res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }
    const result = validateBook(req.body ?? {});
    if (!result.ok) {
      return res.status(400).json({ error: result.error });
    }
    const { title, author, year, isbn } = result.value;
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      title,
      author,
      year,
      isbn,
      id,
    );
    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    return res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: 'book not found' });
    }
    return res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError) {
      return res.status(400).json({ error: 'invalid JSON' });
    }
    return res.status(500).json({ error: 'internal server error' });
  });

  return app;
}
