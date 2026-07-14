import express from 'express';
import {
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook,
  Book,
} from './database';

const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({
      error: 'Validation failed',
      message: 'title and author are required fields',
    });
  }

  const book = createBook(title, author, year, isbn);
  return res.status(201).json(book);
});

// List all books (with optional author filter)
app.get('/books', (req, res) => {
  const { author } = req.query;
  const books = author ? getAllBooks(author as string) : getAllBooks();
  return res.status(200).json(books);
});

// Get a single book by ID
app.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  return res.status(200).json(book);
});

// Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const { title, author, year, isbn } = req.body;
  if (!title && !author && year === undefined && isbn === undefined) {
    return res.status(400).json({ error: 'At least one field is required for update' });
  }

  const book = updateBook(id, { title, author, year, isbn });
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  return res.status(200).json(book);
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const deleted = deleteBook(id);
  if (!deleted) {
    return res.status(404).json({ error: 'Book not found' });
  }

  return res.status(204).send();
});

export { app };
