import express, { type Request, type Response, type NextFunction } from 'express';
import { BookRepository } from './db.js';
import { parseId, validateBook } from './validation.js';

export function createApp(repo: BookRepository) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  app.get('/books', (req, res) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    res.json(repo.list(author));
  });

  app.post('/books', (req, res) => {
    const result = validateBook(req.body);
    if (!result.ok) {
      res.status(400).json({ error: 'validation failed', details: result.errors });
      return;
    }
    res.status(201).json(repo.create(result.value));
  });

  app.get('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: 'invalid id' });
      return;
    }
    const book = repo.get(id);
    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.json(book);
  });

  app.put('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: 'invalid id' });
      return;
    }
    const result = validateBook(req.body);
    if (!result.ok) {
      res.status(400).json({ error: 'validation failed', details: result.errors });
      return;
    }
    const book = repo.update(id, result.value);
    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.json(book);
  });

  app.delete('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: 'invalid id' });
      return;
    }
    if (!repo.delete(id)) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.status(204).send();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: 'not found' });
  });

  // Handles malformed JSON bodies and any unexpected errors.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const e = err as { type?: string; status?: number };
    if (e?.type === 'entity.parse.failed') {
      res.status(400).json({ error: 'malformed JSON body' });
      return;
    }
    res.status(e?.status ?? 500).json({ error: 'internal server error' });
  });

  return app;
}
