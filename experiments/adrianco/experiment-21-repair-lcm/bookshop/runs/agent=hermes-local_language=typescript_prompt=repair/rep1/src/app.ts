import express from 'express';
import path from 'path';
import {
  Book,
  createDatabase,
  generateId,
  closeDatabase,
} from './database';

const PORT = parseInt(process.env.PORT || '3000', 10);

export type { DatabaseStatements } from './database';

function validateBookData(data: Partial<Book>): { errors: string[] } {
  const errors: string[] = [];
  if (!data.title || typeof data.title !== 'string' || data.title.trim() === '') {
    errors.push('Title is required');
  }
  if (!data.author || typeof data.author !== 'string' || data.author.trim() === '') {
    errors.push('Author is required');
  }
  if (data.year !== undefined && data.year !== null) {
    if (!Number.isInteger(data.year) || data.year < 0 || data.year > new Date().getFullYear() + 1) {
      errors.push('Year must be a valid integer between 0 and current year + 1');
    }
  }
  return { errors };
}

export function createApp(dbStatements: import('./database').DatabaseStatements): express.Express {
  const app = express();

  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  app.post('/books', (req, res) => {
    const { title, author, year, isbn } = req.body;
    const { errors } = validateBookData({ title, author, year, isbn });

    if (errors.length > 0) {
      return res.status(400).json({ errors });
    }

    try {
      const id = generateId();
      const result = dbStatements.insertBook.run(id, title, author, year || null, isbn || null) as { changes: number };
      if (result.changes === 0) {
        return res.status(500).json({ errors: ['Failed to insert book'] });
      }
      const book = dbStatements.selectBookById.get(id) as Book;
      if (!book) {
        return res.status(500).json({ errors: ['Failed to retrieve inserted book'] });
      }
      res.status(201).json(book);
    } catch (err: unknown) {
      if (
        err instanceof Error &&
        'code' in err &&
        (err as { code: string }).code === 'SQLITE_CONSTRAINT_UNIQUE'
      ) {
        return res.status(409).json({ errors: ['ISBN already exists'] });
      }
      res.status(500).json({ errors: ['Internal server error'] });
    }
  });

  app.get('/books', (req, res) => {
    const { author } = req.query;

    try {
      let books: Book[];
      if (author && typeof author === 'string' && author.trim() !== '') {
        books = dbStatements.selectBooksByAuthor.all(author) as Book[];
      } else {
        books = dbStatements.selectAllBooks.all() as Book[];
      }
      res.status(200).json(books);
    } catch (_err) {
      res.status(500).json({ errors: ['Internal server error'] });
    }
  });

  app.get('/books/:id', (req, res) => {
    const { id } = req.params;
    const book = dbStatements.selectBookById.get(id) as Book | undefined;

    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    res.status(200).json(book);
  });

  // Update a book - check existence before validation
  app.put('/books/:id', (req, res) => {
    const { id } = req.params;
    const { title, author, year, isbn } = req.body;

    // First check if the book exists
    const existing = dbStatements.selectBookById.get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    // Then validate the input data
    const { errors } = validateBookData({ title, author, year, isbn });
    if (errors.length > 0) {
      return res.status(400).json({ errors });
    }

    try {
      const result = dbStatements.updateBook.run(
        title || null,
        author || null,
        year || null,
        isbn || null,
        id
      ) as { changes: number };

      if (result.changes === 0) {
        return res.status(404).json({ error: 'Book not found' });
      }

      const updated = dbStatements.selectBookById.get(id) as Book;
      res.status(200).json(updated);
    } catch (err: unknown) {
      if (
        err instanceof Error &&
        'code' in err &&
        (err as { code: string }).code === 'SQLITE_CONSTRAINT_UNIQUE'
      ) {
        return res.status(409).json({ errors: ['ISBN already exists'] });
      }
      res.status(500).json({ errors: ['Internal server error'] });
    }
  });

  // Delete a book
  app.delete('/books/:id', (req, res) => {
    const { id } = req.params;
    const existing = dbStatements.selectBookById.get(id) as Book | undefined;

    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    try {
      dbStatements.deleteBook.run(id);
      res.status(200).json({ message: 'Book deleted successfully' });
    } catch (_err) {
      res.status(500).json({ errors: ['Internal server error'] });
    }
  });

  return app;
}

const defaultDb = createDatabase(path.join(__dirname, '..', 'books.db'));
export const app = createApp(defaultDb);

let server: ReturnType<typeof app.listen> | null = null;

export function startServer(port: number): Promise<string> {
  return new Promise((resolve, reject) => {
    server = app.listen(port, () => {
      resolve(`Server running on port ${port}`);
    });
    server.on('error', reject);
  });
}

export function stopServer(): Promise<void> {
  return new Promise((resolve) => {
    if (server) {
      server.close(() => {
        closeDatabase(defaultDb);
        resolve();
      });
    } else {
      resolve();
    }
  });
}

if (require.main === module) {
  startServer(PORT)
    .then((msg) => console.log(msg))
    .catch((err) => {
      console.error('Failed to start server:', err);
      process.exit(1);
    });
}
