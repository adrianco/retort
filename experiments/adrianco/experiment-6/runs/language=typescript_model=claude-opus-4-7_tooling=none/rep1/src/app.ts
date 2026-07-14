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

function validateBook(body: BookInput, partial = false): { ok: true; value: Partial<ValidatedBook> } | { ok: false; error: string } {
  const result: Partial<ValidatedBook> = {};

  if (body.title !== undefined) {
    if (typeof body.title !== 'string' || body.title.trim() === '') {
      return { ok: false, error: 'title must be a non-empty string' };
    }
    result.title = body.title.trim();
  } else if (!partial) {
    return { ok: false, error: 'title is required' };
  }

  if (body.author !== undefined) {
    if (typeof body.author !== 'string' || body.author.trim() === '') {
      return { ok: false, error: 'author must be a non-empty string' };
    }
    result.author = body.author.trim();
  } else if (!partial) {
    return { ok: false, error: 'author is required' };
  }

  if (body.year !== undefined && body.year !== null) {
    if (typeof body.year !== 'number' || !Number.isInteger(body.year)) {
      return { ok: false, error: 'year must be an integer' };
    }
    result.year = body.year;
  } else if (body.year === null) {
    result.year = null;
  }

  if (body.isbn !== undefined && body.isbn !== null) {
    if (typeof body.isbn !== 'string') {
      return { ok: false, error: 'isbn must be a string' };
    }
    result.isbn = body.isbn.trim();
  } else if (body.isbn === null) {
    result.isbn = null;
  }

  return { ok: true, value: result };
}

export function createApp(db: Database) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const validation = validateBook(req.body ?? {}, false);
    if (!validation.ok) {
      return res.status(400).json({ error: validation.error });
    }
    const { title, author, year, isbn } = validation.value;
    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(title!, author!, year ?? null, isbn ?? null);
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(info.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author;
    let books: Book[];
    if (typeof author === 'string' && author.length > 0) {
      books = db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }
    res.status(200).json(books);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }
    const validation = validateBook(req.body ?? {}, true);
    if (!validation.ok) {
      return res.status(400).json({ error: validation.error });
    }
    const merged: Book = {
      id: existing.id,
      title: validation.value.title ?? existing.title,
      author: validation.value.author ?? existing.author,
      year: validation.value.year !== undefined ? validation.value.year : existing.year,
      isbn: validation.value.isbn !== undefined ? validation.value.isbn : existing.isbn,
    };
    db.prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    ).run(merged.title, merged.author, merged.year, merged.isbn, id);
    res.status(200).json(merged);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    res.status(500).json({ error: err.message || 'internal server error' });
  });

  return app;
}
