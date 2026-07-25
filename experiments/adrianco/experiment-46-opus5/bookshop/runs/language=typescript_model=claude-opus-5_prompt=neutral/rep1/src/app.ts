import express, { type NextFunction, type Request, type Response } from 'express';
import { BookStore, DuplicateIsbnError } from './db.js';
import { parseId, validateBookInput } from './validation.js';
import type { FieldError } from './types.js';

/** Sends the API's uniform error envelope. */
function sendError(
  res: Response,
  status: number,
  message: string,
  details?: FieldError[],
): void {
  const body: { error: string; details?: FieldError[] } = { error: message };
  if (details !== undefined && details.length > 0) body.details = details;
  res.status(status).json(body);
}

export function createApp(store: BookStore): express.Express {
  const app = express();

  app.use(express.json({ limit: '100kb' }));

  // GET /health — liveness plus a real round-trip to the database.
  app.get('/health', (_req: Request, res: Response) => {
    try {
      store.ping();
      res.status(200).json({ status: 'ok', database: 'ok' });
    } catch {
      res.status(503).json({ status: 'error', database: 'unavailable' });
    }
  });

  // POST /books — create a book.
  app.post('/books', (req: Request, res: Response) => {
    const result = validateBookInput(req.body);
    if (!result.ok) {
      sendError(res, 400, 'validation failed', result.errors);
      return;
    }
    try {
      const book = store.create(result.value);
      res.status(201).location(`/books/${book.id}`).json(book);
    } catch (err) {
      if (err instanceof DuplicateIsbnError) {
        sendError(res, 409, err.message);
        return;
      }
      throw err;
    }
  });

  // GET /books — list books, optionally filtered by exact author.
  app.get('/books', (req: Request, res: Response) => {
    const raw = req.query['author'];
    if (raw !== undefined && typeof raw !== 'string') {
      sendError(res, 400, 'validation failed', [
        { field: 'author', message: 'author filter must be a single value' },
      ]);
      return;
    }
    const author = raw === undefined ? undefined : raw.trim();
    res.status(200).json(store.list(author));
  });

  // GET /books/:id — fetch one book.
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      sendError(res, 400, 'id must be a positive integer');
      return;
    }
    const book = store.get(id);
    if (book === null) {
      sendError(res, 404, `book ${id} not found`);
      return;
    }
    res.status(200).json(book);
  });

  // PUT /books/:id — replace a book.
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      sendError(res, 400, 'id must be a positive integer');
      return;
    }
    const result = validateBookInput(req.body);
    if (!result.ok) {
      sendError(res, 400, 'validation failed', result.errors);
      return;
    }
    try {
      const book = store.update(id, result.value);
      if (book === null) {
        sendError(res, 404, `book ${id} not found`);
        return;
      }
      res.status(200).json(book);
    } catch (err) {
      if (err instanceof DuplicateIsbnError) {
        sendError(res, 409, err.message);
        return;
      }
      throw err;
    }
  });

  // DELETE /books/:id — remove a book.
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      sendError(res, 400, 'id must be a positive integer');
      return;
    }
    if (!store.delete(id)) {
      sendError(res, 404, `book ${id} not found`);
      return;
    }
    res.status(204).end();
  });

  app.use((_req: Request, res: Response) => {
    sendError(res, 404, 'not found');
  });

  // Express only treats a 4-arg function as an error handler, so `_next` stays.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    // A malformed JSON body surfaces here from express.json().
    if (
      err instanceof SyntaxError &&
      'status' in err &&
      (err as { status?: unknown }).status === 400
    ) {
      sendError(res, 400, 'request body is not valid JSON');
      return;
    }
    if (err instanceof Error && (err as { type?: unknown }).type === 'entity.too.large') {
      sendError(res, 413, 'request body too large');
      return;
    }
    console.error('unhandled error:', err);
    sendError(res, 500, 'internal server error');
  });

  return app;
}
