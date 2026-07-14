import express, { Request, Response, NextFunction } from 'express';
import { BookDatabase, Book } from './database';

export function createApp(dbPath?: string): { app: express.Application; server: any } {
  const db = new BookDatabase(dbPath);

  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Create a new book
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;

    if (!title || !author) {
      const errors: string[] = [];
      if (!title) errors.push('title is required');
      if (!author) errors.push('author is required');
      return res.status(400).json({ error: errors.join('. ') });
    }

    const book = db.create(title, author, year || null, isbn || null);
    return res.status(201).json(book);
  });

  // List all books (with optional author filter)
  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author as string | undefined;
    const books = db.findAll(author);
    return res.status(200).json(books);
  });

  // Get a single book by ID
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = String(req.params.id);
    const book = db.findById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(200).json(book);
  });

  // Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;
    const id = String(req.params.id);

    // Validate required fields: title and author must always be present
    if (title === undefined || !title) {
      return res.status(400).json({ error: 'title is required' });
    }
    if (author === undefined || !author) {
      return res.status(400).json({ error: 'author is required' });
    }

    const updates: Partial<Pick<Book, 'title' | 'author' | 'year' | 'isbn'>> = {};
    updates.title = title;
    if (author !== undefined) updates.author = author;
    if (year !== undefined) updates.year = year;
    if (isbn !== undefined) updates.isbn = isbn;

    const book = db.update(id, updates);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(200).json(book);
  });

  // Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = String(req.params.id);
    const book = db.delete(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.status(200).json(book);
  });

  const server = app.listen(0);

  return { app, server };
}

// For running standalone
if (require.main === module) {
  const { server } = createApp();
  server.listen(3000, () => {
    console.log('Book API running on http://localhost:3000');
  });
}
