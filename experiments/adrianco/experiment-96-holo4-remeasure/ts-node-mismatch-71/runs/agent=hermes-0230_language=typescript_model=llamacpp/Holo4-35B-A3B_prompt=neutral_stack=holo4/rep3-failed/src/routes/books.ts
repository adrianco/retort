import { Router, Request, Response } from 'express';
import { db } from '../db';
import { validateBook, BookInput } from '../validation';

const router = Router();

interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

router.post('/', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  const errors = validateBook({ title, author, year, isbn });

  if (errors.length > 0) {
    return res.status(400).json({ errors });
  }

  try {
    const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
    const result = stmt.run(title.trim(), author.trim(), year || null, isbn || null);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    res.status(201).json(book);
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/', (req: Request, res: Response) => {
  const { author } = req.query;

  if (author) {
    const books = db.prepare('SELECT * FROM books WHERE author = ?').all(author as string) as Book[];
    return res.json(books);
  }

  const books = db.prepare('SELECT * FROM books').all() as Book[];
  res.json(books);
});

router.get('/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

router.put('/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, isbn } = req.body;
  const updates: string[] = [];
  const values: any[] = [];

  if (title !== undefined) {
    updates.push('title = ?');
    values.push(title.trim());
  }
  if (author !== undefined) {
    updates.push('author = ?');
    values.push(author.trim());
  }
  if (year !== undefined) {
    updates.push('year = ?');
    values.push(year);
  }
  if (isbn !== undefined) {
    updates.push('isbn = ?');
    values.push(isbn || null);
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: 'No valid fields to update' });
  }

  values.push(id);

  try {
    db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`).run(...values);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    res.json(book);
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.delete('/:id', (req: Request, res: Response) => {
  const { id } = req.params;
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.status(204).send();
});

export default router;
