import express, { Request, Response, NextFunction } from 'express';
import Database, { Book } from './database';
import path from 'path';

const app = express();
const PORT = process.env.PORT || 3000;
const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'books.db');

// Initialize database
const db = new Database(DB_PATH);

// Middleware
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books — Create a new book
app.post('/books', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { title, author, year, isbn } = req.body;

    // Validation
    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'Author is required' });
    }
    if (!year || typeof year !== 'number' || !Number.isInteger(year)) {
      return res.status(400).json({ error: 'Year is required and must be an integer' });
    }
    if (!isbn || typeof isbn !== 'string' || isbn.trim() === '') {
      return res.status(400).json({ error: 'ISBN is required' });
    }

    const book = await db.createBook(title.trim(), author.trim(), year, isbn.trim());
    res.status(201).json(book);
  } catch (error) {
    if ((error as Error).message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    next(error);
  }
});

// GET /books — List all books (with optional ?author= filter)
app.get('/books', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { author } = req.query;
    const books = author ? await db.getAllBooks(author as string) : await db.getAllBooks();
    res.status(200).json(books);
  } catch (error) {
    next(error);
  }
});

// GET /books/:id — Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const book = await db.getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch (error) {
    next(error);
  }
});

// PUT /books/:id — Update a book
app.put('/books/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const { title, author, year, isbn } = req.body;

    // At least one field to update
    if (title === undefined && author === undefined && year === undefined && isbn === undefined) {
      return res.status(400).json({ error: 'At least one field to update is required' });
    }

    // Validate provided fields
    if (title !== undefined) {
      if (typeof title !== 'string' || title.trim() === '') {
        return res.status(400).json({ error: 'Title must be a non-empty string' });
      }
    }
    if (author !== undefined) {
      if (typeof author !== 'string' || author.trim() === '') {
        return res.status(400).json({ error: 'Author must be a non-empty string' });
      }
    }
    if (year !== undefined) {
      if (typeof year !== 'number' || !Number.isInteger(year)) {
        return res.status(400).json({ error: 'Year must be an integer' });
      }
    }
    if (isbn !== undefined) {
      if (typeof isbn !== 'string' || isbn.trim() === '') {
        return res.status(400).json({ error: 'ISBN must be a non-empty string' });
      }
    }

    const book = await db.updateBook(
      id,
      title !== undefined ? title.trim() : undefined,
      author !== undefined ? author.trim() : undefined,
      year,
      isbn !== undefined ? isbn.trim() : undefined
    );

    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch (error) {
    if ((error as Error).message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    next(error);
  }
});

// DELETE /books/:id — Delete a book
app.delete('/books/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const deleted = await db.deleteBook(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    next(error);
  }
});

// Error handling middleware
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server only when not in test mode
if (require.main === module) {
  const server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });

  // Graceful shutdown
  process.on('SIGINT', async () => {
    await db.close();
    server.close();
    process.exit(0);
  });
}

// Export app and db for testing
export { app, db };
export default app;
