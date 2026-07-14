import express, { Express, Request, Response, NextFunction } from 'express';
import Database from 'better-sqlite3';
import {
  createDb,
  insertBook,
  listBooks,
  getBook,
  updateBook,
  deleteBook,
} from './db';
import { validateBook } from './validation';

/**
 * Build the Express application around a given database handle.
 * Keeping the db injectable makes the app easy to test in isolation.
 */
export function createApp(db: Database.Database = createDb()): Express {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Create
  app.post('/books', (req: Request, res: Response) => {
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = insertBook(db, result.value!);
    res.status(201).json(book);
  });

  // List (optional ?author= filter)
  app.get('/books', (req: Request, res: Response) => {
    const author =
      typeof req.query.author === 'string' ? req.query.author : undefined;
    res.status(200).json(listBooks(db, author));
  });

  // Read one
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const book = getBook(db, id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  });

  // Update
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = updateBook(db, id, result.value!);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  });

  // Delete
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const deleted = deleteBook(db, id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(204).send();
  });

  // JSON parse / fallthrough error handler
  app.use(
    (err: Error, _req: Request, res: Response, _next: NextFunction) => {
      if (err instanceof SyntaxError && 'body' in err) {
        return res.status(400).json({ error: 'Malformed JSON body' });
      }
      res.status(500).json({ error: 'Internal server error' });
    }
  );

  return app;
}

function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  return parseInt(raw, 10);
}
