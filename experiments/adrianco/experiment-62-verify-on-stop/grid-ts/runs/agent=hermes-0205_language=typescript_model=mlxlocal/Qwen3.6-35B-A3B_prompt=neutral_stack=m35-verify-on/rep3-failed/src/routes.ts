import { Router } from 'express';
import { getAllBooks, getBookById, createBook, updateBook, deleteBook, db } from './database';

const router = Router();

router.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

router.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const book = createBook(title, author, year, isbn);
  res.status(201).json(book);
});

router.get('/books', (req, res) => {
  const { author } = req.query;
  const books = getAllBooks(author as string | undefined);
  res.json(books);
});

router.get('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

router.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const { title, author, year, isbn } = req.body;

  if (!title && !author) {
    return res.status(400).json({ error: 'At least one field (title or author) must be provided' });
  }

  const book = updateBook(id, title, author, year, isbn);
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

router.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id, 10);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const deleted = deleteBook(id);
  if (!deleted) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.status(204).send();
});

export default router;
