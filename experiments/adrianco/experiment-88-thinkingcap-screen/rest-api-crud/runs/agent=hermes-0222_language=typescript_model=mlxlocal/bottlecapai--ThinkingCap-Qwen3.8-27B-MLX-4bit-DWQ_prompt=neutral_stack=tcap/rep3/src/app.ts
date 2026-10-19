import express, { type NextFunction, type Request, type Response } from 'express';
import type { DatabaseSync } from 'node:sqlite';
import * as store from './db.js';
import { validateBookPayload } from './validation.js';

/**
 * Build the Express application wired to the given database handle.
 * Exported as a factory so tests can inject an in-memory database.
 */
export function createApp(database: DatabaseSync): express.Express {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', uptime: process.uptime() });
  });

  // Root: service info
  app.get('/', (_req: Request, res: Response) => {
    res.json({
      name: 'book-api',
      status: 'ok',
      endpoints: [
        'GET /health',
        'POST /books',
        'GET /books',
        'GET /books/:id',
        'PUT /books/:id',
        'DELETE /books/:id',
      ],
    });
  });

  // Create a book
  app.post('/books', (req: Request, res: Response) => {
    const { patch, errors } = validateBookPayload(req.body);
    if (errors.length > 0 || patch === null) {
      res.status(400).json({ error: errors.join('; ') });
      return;
    }
    const book = store.createBook(database, patch as store.BookFields);
    res.status(201).json(book);
  });

  // List books (optional ?author= filter, case-insensitive)
  app.get('/books', (req: Request, res: Response) => {
    const rawAuthor = req.query.author;
    const author =
      typeof rawAuthor === 'string' && rawAuthor.trim().length > 0
        ? rawAuthor.trim()
        : undefined;
    res.json(store.listBooks(database, author));
  });

  // Parse and validate the :id path parameter; replies 400 on bad input.
  const parseId = (req: Request, res: Response): number | null => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return null;
    }
    return id;
  };

  // Get one book
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req, res);
    if (id === null) return;
    const book = store.getBook(database, id);
    if (!book) {
      res.status(404).json({ error: `book ${id} not found` });
      return;
    }
    res.json(book);
  });

  // Update a book (partial: only provided fields are changed)
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req, res);
    if (id === null) return;
    const { patch, errors } = validateBookPayload(req.body, { partial: true });
    if (errors.length > 0 || patch === null) {
      res.status(400).json({ error: errors.join('; ') });
      return;
    }
    const book = store.updateBook(database, id, patch);
    if (!book) {
      res.status(404).json({ error: `book ${id} not found` });
      return;
    }
    res.json(book);
  });

  // Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req, res);
    if (id === null) return;
    const deleted = store.deleteBook(database, id);
    if (!deleted) {
      res.status(404).json({ error: `book ${id} not found` });
      return;
    }
    res.status(204).end();
  });

  // Unknown route
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: 'Not found' });
  });

  // Central error handler (malformed JSON body, unexpected errors)
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const e = err as { type?: string; status?: number };
    if (e?.type === 'entity.parse.failed' || err instanceof SyntaxError) {
      res.status(400).json({ error: 'Invalid JSON body' });
      return;
    }
    console.error('Unhandled error:', err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
