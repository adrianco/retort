import { Router } from 'express';
import { BookDatabase } from '../types';
import { validateBookInput, validateBookUpdate } from '../middleware/validation';

const router = Router();
const db = new BookDatabase('./books.db');

// Initialize database on module load
db.initialize();

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Get all books (with optional author filter)
router.get('/books', async (req, res) => {
  try {
    const author = req.query.author as string | undefined;
    const books = await db.getAllBooks(author);
    res.json({ books, count: books.length });
  } catch (error) {
    console.error('Error getting books:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get a single book by ID
router.get('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const book = await db.getBookById(id);
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.json({ book });
  } catch (error) {
    console.error('Error getting book:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create a new book with validation
router.post('/books', validateBookInput, async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    const book = await db.createBook({ title, author, year: year || 0, isbn: isbn || '' });
    res.status(201).json({ book });
  } catch (error) {
    console.error('Error creating book:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book with validation
router.put('/books/:id', validateBookUpdate, async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const { title, author, year, isbn } = req.body;
    const book = await db.updateBook(id, { title, author, year, isbn });
    
    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.json({ book });
  } catch (error) {
    console.error('Error updating book:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
router.delete('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      res.status(400).json({ error: 'Invalid book ID' });
      return;
    }

    const deleted = await db.deleteBook(id);
    if (!deleted) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(204).send();
  } catch (error) {
    console.error('Error deleting book:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
