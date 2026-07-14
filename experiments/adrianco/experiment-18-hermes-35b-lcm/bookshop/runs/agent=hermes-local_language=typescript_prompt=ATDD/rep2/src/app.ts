import express from 'express';
import type { Request, Response } from 'express';
import Database from 'better-sqlite3';

type DB = Database.Database;

import {
  createDb,
  getAllBooks,
  getBook,
  updateBook,
  deleteBook,
  createBook,
  setAppDb,
  shutdownDb,
} from './db';
import { validateBook, BookInput } from './validation';

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3456;

function createApp(db: DB): express.Express {
  const app = express();
  app.use(express.json());
  setAppDb(db);

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Create a book
  app.post('/books', (_req: Request, res: Response) => {
    const input: BookInput = _req.body;
    const validation = validateBook(input);
    if (!validation.valid) {
      return res.status(400).json({ error: validation.error });
    }
    const book = createBook(db, input.title!, input.author!, input.year, input.isbn);
    res.status(201).json(book);
  });

  // List all books (with optional ?author= filter)
  app.get('/books', (_req: Request, res: Response) => {
    const authorParam = _req.query.author;
    const author = typeof authorParam === 'string' ? authorParam : undefined;
    const books = getAllBooks(db, author);
    res.status(200).json({ books });
  });

  // Get a single book
  app.get('/books/:id', (req: Request<{ id: string }>, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const book = getBook(db, id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  });

  // Update a book
  app.put('/books/:id', (req: Request<{ id: string }>, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const input: BookInput = req.body;
    const validation = validateBook(input);
    if (!validation.valid) {
      return res.status(400).json({ error: validation.error });
    }
    const book = updateBook(db, id, input.title!, input.author!, input.year, input.isbn);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  });

  // Delete a book
  app.delete('/books/:id', (req: Request<{ id: string }>, res: Response) => {
    const id = parseInt(req.params.id, 10);
    const book = deleteBook(db, id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json({ message: 'Book deleted' });
  });

  return app;
}

function startServer(app: express.Express): void {
  app.listen(PORT, () => {
    console.log(`Book API server running on port ${PORT}`);
  });
}

export { createApp, startServer, shutdownDb };

// Only start if running directly (not imported for tests)
if (require.main === module) {
  const db = createDb('./books.db');
  const app = createApp(db);
  startServer(app);
}
