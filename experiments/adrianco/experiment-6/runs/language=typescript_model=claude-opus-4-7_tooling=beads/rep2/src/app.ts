import express, { Request, Response, NextFunction } from 'express';
import { BookStore, BookInput } from './db';

function validateBookInput(body: unknown): { ok: true; value: BookInput } | { ok: false; error: string } {
  if (!body || typeof body !== 'object') {
    return { ok: false, error: 'Request body must be a JSON object' };
  }
  const b = body as Record<string, unknown>;
  if (typeof b.title !== 'string' || b.title.trim() === '') {
    return { ok: false, error: 'title is required and must be a non-empty string' };
  }
  if (typeof b.author !== 'string' || b.author.trim() === '') {
    return { ok: false, error: 'author is required and must be a non-empty string' };
  }
  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== 'number' || !Number.isInteger(b.year)) {
      return { ok: false, error: 'year must be an integer' };
    }
    year = b.year;
  }
  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== 'string') {
      return { ok: false, error: 'isbn must be a string' };
    }
    isbn = b.isbn;
  }
  return {
    ok: true,
    value: { title: b.title.trim(), author: b.author.trim(), year, isbn },
  };
}

function parseId(raw: unknown): number | null {
  if (typeof raw !== 'string') return null;
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}

export function createApp(store: BookStore): express.Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const result = validateBookInput(req.body);
    if (!result.ok) {
      return res.status(400).json({ error: result.error });
    }
    const book = store.create(result.value);
    return res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const authorFilter = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = store.list(authorFilter);
    return res.status(200).json(books);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const book = store.getById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const result = validateBookInput(req.body);
    if (!result.ok) {
      return res.status(400).json({ error: result.error });
    }
    const updated = store.update(id, result.value);
    if (!updated) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be a positive integer' });
    }
    const deleted = store.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError && 'body' in err) {
      return res.status(400).json({ error: 'Invalid JSON body' });
    }
    return res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
