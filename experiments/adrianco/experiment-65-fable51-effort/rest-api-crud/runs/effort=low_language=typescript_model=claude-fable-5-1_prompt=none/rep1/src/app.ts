import express, { type Request, type Response, type NextFunction } from 'express';
import { BookRepository } from './db.js';
import { validateBook, parseId } from './validation.js';

export function createApp(repo: BookRepository) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  app.post('/books', (req, res) => {
    const result = validateBook(req.body);
    if (!result.ok) return res.status(400).json({ errors: result.errors });
    res.status(201).json(repo.create(result.value));
  });

  app.get('/books', (req, res) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    res.json(repo.list(author));
  });

  app.get('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    const book = id === undefined ? undefined : repo.get(id);
    if (!book) return res.status(404).json({ error: 'book not found' });
    res.json(book);
  });

  app.put('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) return res.status(404).json({ error: 'book not found' });
    const result = validateBook(req.body);
    if (!result.ok) return res.status(400).json({ errors: result.errors });
    const book = repo.update(id, result.value);
    if (!book) return res.status(404).json({ error: 'book not found' });
    res.json(book);
  });

  app.delete('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined || !repo.delete(id)) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(204).send();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: 'not found' });
  });

  // Malformed JSON and other errors
  app.use((err: Error & { type?: string }, _req: Request, res: Response, _next: NextFunction) => {
    if (err.type === 'entity.parse.failed') {
      return res.status(400).json({ error: 'invalid JSON body' });
    }
    res.status(500).json({ error: 'internal server error' });
  });

  return app;
}
