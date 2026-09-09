import express, { type ErrorRequestHandler } from 'express';
import { BookStore, type BookInput } from './store.js';

class BadRequest extends Error {}

function validateBook(value: unknown): BookInput {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new BadRequest('Body must be a JSON object');
  }
  const input = value as Record<string, unknown>;
  for (const field of ['title', 'author'] as const) {
    if (typeof input[field] !== 'string' || !input[field].trim()) {
      throw new BadRequest(`${field} is required and must be a non-empty string`);
    }
  }
  if (input.year != null && (typeof input.year !== 'number' || !Number.isSafeInteger(input.year))) {
    throw new BadRequest('year must be a safe integer or null');
  }
  if (input.isbn != null && (typeof input.isbn !== 'string' || !input.isbn.trim())) {
    throw new BadRequest('isbn must be a non-empty string or null');
  }
  return {
    title: (input.title as string).trim(),
    author: (input.author as string).trim(),
    year: (input.year as number | undefined | null) ?? null,
    isbn: typeof input.isbn === 'string' ? input.isbn.trim() : null,
  };
}

export function createApp(store: BookStore) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '100kb' }));

  app.get('/health', (_req, res) => {
    res.status(store.healthy() ? 200 : 503).json({ status: 'ok' });
  });
  app.post('/books', (req, res) => {
    const book = store.create(validateBook(req.body));
    res.location(`/books/${book.id}`).status(201).json(book);
  });
  app.get('/books', (req, res) => {
    const author = req.query.author;
    if (author !== undefined && typeof author !== 'string') {
      throw new BadRequest('author filter must be a single string');
    }
    res.json(store.list(author));
  });
  app.param('id', (_req, res, next, value: string) => {
    if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) {
      res.status(400).json({ error: 'id must be a positive safe integer' });
      return;
    }
    next();
  });
  app.get('/books/:id', (req, res) => {
    const book = store.get(Number(req.params.id));
    if (!book) { res.status(404).json({ error: 'Book not found' }); return; }
    res.json(book);
  });
  app.put('/books/:id', (req, res) => {
    const book = store.update(Number(req.params.id), validateBook(req.body));
    if (!book) { res.status(404).json({ error: 'Book not found' }); return; }
    res.json(book);
  });
  app.delete('/books/:id', (req, res) => {
    if (!store.delete(Number(req.params.id))) {
      res.status(404).json({ error: 'Book not found' }); return;
    }
    res.json({ message: 'Book deleted' });
  });
  app.use((_req, res) => { res.status(404).json({ error: 'Route not found' }); });
  const errorHandler: ErrorRequestHandler = (error, _req, res, _next) => {
    if (error instanceof BadRequest || error.type === 'entity.parse.failed') {
      res.status(400).json({ error: error instanceof BadRequest ? error.message : 'Invalid JSON body' });
    } else if (error.type === 'entity.too.large') {
      res.status(413).json({ error: 'Request body too large' });
    } else if (error.status === 415) {
      res.status(415).json({ error: 'Unsupported body encoding or charset' });
    } else {
      res.status(500).json({ error: 'Internal server error' });
    }
  };
  app.use(errorHandler);
  return app;
}
