import express, { Request, Response, NextFunction } from 'express';
import { BookRepository, createDatabase } from './db';
import { validateBook } from './validation';

export interface AppOptions {
  dbFile?: string;
}

export function createApp(options: AppOptions = {}) {
  const db = createDatabase(options.dbFile ?? ':memory:');
  const repo = new BookRepository(db);

  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const result = validateBook(req.body);
    if (!result.valid || !result.value) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = repo.create(result.value);
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    res.status(200).json(repo.list(author));
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ errors: ['id must be a positive integer'] });
    }
    const book = repo.getById(id);
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ errors: ['id must be a positive integer'] });
    }
    const result = validateBook(req.body);
    if (!result.valid || !result.value) {
      return res.status(400).json({ errors: result.errors });
    }
    const updated = repo.update(id, result.value);
    if (!updated) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ errors: ['id must be a positive integer'] });
    }
    const deleted = repo.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(204).send();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError && 'body' in err) {
      return res.status(400).json({ errors: ['invalid JSON body'] });
    }
    res.status(500).json({ error: 'internal server error' });
  });

  return { app, db, repo };
}
