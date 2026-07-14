import express, { Request, Response, NextFunction } from 'express';
import { BookStore } from './db';
import { parseId, validateBookInput } from './validation';

export function createApp(store: BookStore): express.Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const result = validateBookInput(req.body);
    if (!result.ok || !result.value) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = store.create(result.value);
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = store.list(author);
    res.status(200).json(books);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ['Invalid id'] });
    }
    const book = store.get(id);
    if (!book) {
      return res.status(404).json({ errors: ['Book not found'] });
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ['Invalid id'] });
    }
    const result = validateBookInput(req.body);
    if (!result.ok || !result.value) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = store.update(id, result.value);
    if (!book) {
      return res.status(404).json({ errors: ['Book not found'] });
    }
    res.status(200).json(book);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ['Invalid id'] });
    }
    const ok = store.delete(id);
    if (!ok) {
      return res.status(404).json({ errors: ['Book not found'] });
    }
    res.status(204).send();
  });

  // JSON parse error handler
  app.use((err: Error & { status?: number; type?: string }, _req: Request, res: Response, next: NextFunction) => {
    if (err.type === 'entity.parse.failed') {
      return res.status(400).json({ errors: ['Invalid JSON body'] });
    }
    next(err);
  });

  return app;
}
