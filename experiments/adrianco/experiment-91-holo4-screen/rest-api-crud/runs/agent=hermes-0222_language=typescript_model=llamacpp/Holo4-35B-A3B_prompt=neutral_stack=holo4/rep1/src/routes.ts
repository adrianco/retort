import { Router } from 'express';
import { getDb } from './database';
import { validateBook, validatePartialBook } from './middleware';
import { CreateBookInput, UpdateBookInput, ValidationError } from './types';

const router = Router();

// POST /books - Create a new book
router.post('/books', (req, res) => {
  const input: CreateBookInput = req.body;
  const errors = validateBook(input);
  if (errors.length > 0) {
    return res.status(400).json({ error: 'Validation error', details: errors });
  }

  try {
    const stmt = getDb().prepare(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`);
    const result = stmt.run(input.title, input.author, input.year, input.isbn);
    const book = getDb().prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as any;
    res.status(201).json(book);
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    throw err;
  }
});

// GET /books - List all books (support ?author= filter)
router.get('/books', (req, res) => {
  const { author } = req.query;
  let books: any[];

  if (author && typeof author === 'string') {
    const stmt = getDb().prepare('SELECT * FROM books WHERE author = ?');
    books = stmt.all(author);
  } else {
    const stmt = getDb().prepare('SELECT * FROM books ORDER BY id');
    books = stmt.all();
  }

  res.json(books);
});

// GET /books/:id - Get a single book by ID
router.get('/books/:id', (req, res, next) => {
  const { id } = req.params;
  const book = getDb().prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!book) {
    throw { type: 'not_found', message: `Book with ID ${id} not found` };
  }
  res.json(book);
});

// PUT /books/:id - Update a book
router.put('/books/:id', (req, res, next) => {
  const { id } = req.params;
  const existing = getDb().prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) {
    throw { type: 'not_found', message: `Book with ID ${id} not found` };
  }

  const input: UpdateBookInput = req.body;
  const errors = validatePartialBook(input);
  if (errors.length > 0) {
    return res.status(400).json({ error: 'Validation error', details: errors });
  }

  try {
    const updates: string[] = [];
    const values: any[] = [];

    if (input.title !== undefined) { updates.push('title = ?'); values.push(input.title); }
    if (input.author !== undefined) { updates.push('author = ?'); values.push(input.author); }
    if (input.year !== undefined) { updates.push('year = ?'); values.push(input.year); }
    if (input.isbn !== undefined) { updates.push('isbn = ?'); values.push(input.isbn); }

    if (updates.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    values.push(id);
    const stmt = getDb().prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`);
    stmt.run(...values);

    const updated = getDb().prepare('SELECT * FROM books WHERE id = ?').get(id) as any;
    res.json(updated);
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    throw err;
  }
});

// DELETE /books/:id - Delete a book
router.delete('/books/:id', (req, res, next) => {
  const { id } = req.params;
  const existing = getDb().prepare('SELECT * FROM books WHERE id = ?').get(id);
  if (!existing) {
    throw { type: 'not_found', message: `Book with ID ${id} not found` };
  }

  getDb().prepare('DELETE FROM books WHERE id = ?').run(id);
  res.status(204).send();
});

export default router;
