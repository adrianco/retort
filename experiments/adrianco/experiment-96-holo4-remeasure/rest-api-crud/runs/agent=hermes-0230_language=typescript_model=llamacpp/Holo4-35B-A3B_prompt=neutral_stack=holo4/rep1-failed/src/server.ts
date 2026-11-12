import express, { Request, Response, NextFunction } from 'express';
import { createBook, getAllBooks, getBookById, updateBook, deleteBook } from './database';
import { CreateBookInput, UpdateBookInput } from './types';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Create a new book
app.post('/books', async (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body as CreateBookInput;

    // Validate required fields
    if (!title || !title.trim()) {
      return res.status(400).json({ error: 'Title is required' });
    }
    if (!author || !author.trim()) {
      return res.status(400).json({ error: 'Author is required' });
    }
    if (!year || typeof year !== 'number' || year < 0) {
      return res.status(400).json({ error: 'Year is required and must be a positive number' });
    }
    if (!isbn || !isbn.trim()) {
      return res.status(400).json({ error: 'ISBN is required' });
    }

    const book = await createBook(title.trim(), author.trim(), year, isbn.trim());
    res.status(201).json(book);
  } catch (err: any) {
    if (err.message && err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// List all books (with optional author filter)
app.get('/books', async (req: Request, res: Response) => {
  try {
    const { author } = req.query;
    const books = author ? await getAllBooks(author as string) : await getAllBooks();
    res.status(200).json(books);
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    const book = await getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book
app.put('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const { title, author, year, isbn } = req.body as UpdateBookInput;

    // Validate at least one field provided
    if (title === undefined && author === undefined && year === undefined && !isbn) {
      return res.status(400).json({ error: 'At least one field to update is required' });
    }

    const book = await updateBook(id, title, author, year, isbn);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch (err: any) {
    if (err.message && err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
app.delete('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    const deleted = await deleteBook(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(204).send();
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export { app, PORT };
