import express, {
  type Express,
  type Request,
  type Response,
  type NextFunction,
} from 'express';
import type { Database } from 'better-sqlite3';
import { booksRouter } from './books';

/** Build the Express app around an already-opened SQLite database. */
export function createApp(db: Database): Express {
  const app = express();

  app.use(express.json());

  // Malformed JSON body -> 400 (instead of Express's default HTML 400/500).
  app.use((err: unknown, req: Request, res: Response, next: NextFunction) => {
    if (err instanceof SyntaxError && 'body' in (err as object)) {
      res.status(400).json({ error: 'Request body is not valid JSON' });
      return;
    }
    next(err);
  });

  // GET /health — health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  app.use('/books', booksRouter(db));

  // JSON 404 for unknown routes.
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: 'Not found' });
  });

  // Generic JSON 500 for anything else.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
