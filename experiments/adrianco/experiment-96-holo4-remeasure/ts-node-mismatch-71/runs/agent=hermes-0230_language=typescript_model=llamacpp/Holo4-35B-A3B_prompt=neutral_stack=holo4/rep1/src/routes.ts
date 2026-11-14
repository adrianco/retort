import express, { Request, Response } from 'express';
import { getAllBooks, getBookById, createBook, updateBook, deleteBook } from './database';
import { validateCreateBook, validateUpdateBook } from './validation';

const router = express.Router();

// Health check
router.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'OK' });
});

// List all books
router.get('/books', (req: Request, res: Response) => {
  const author = req.query.author as string | undefined;
  const books = getAllBooks(author);
  res.status(200).json(books);
});

// Get a single book
router.get('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.status(200).json(book);
});

// Create a new book
router.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  const validation = validateCreateBook(title, author, year, isbn);
  if (!validation.valid) {
    return res.status(400).json({ errors: validation.errors });
  }

  try {
    const book = createBook(title, author, year, isbn);
    res.status(201).json(book);
  } catch (err: any) {
    if (err.message && err.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book
router.put('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const validation = validateUpdateBook(req.body);
  if (!validation.valid) {
    return res.status(400).json({ errors: validation.errors });
  }

  try {
    const updated = updateBook(id, req.body);
    res.status(200).json(updated);
  } catch (err: any) {
    if (err.message && err.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
router.delete('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  deleteBook(id);
  res.status(204).send();
});

export default router;
