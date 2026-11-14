import express, { Request, Response } from 'express';
import { db } from './database';
import { Book, CreateBookInput, UpdateBookInput } from './types';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// GET /books — list all books (support ?author= filter)
app.get('/books', (req: Request, res: Response) => {
  try {
    const { author } = req.query;
    let books: Book[];
    if (author && typeof author === 'string') {
      books = db.prepare('SELECT * FROM books WHERE author = ?').all(author) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books').all() as Book[];
    }
    res.status(200).json(books);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// POST /books — create a new book
app.post('/books', (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body;

    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }

    const result = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title, author, year || null, isbn || null);

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    res.status(201).json(book);
  } catch (err) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// GET /books/:id — get a single book
app.get('/books/:id', (req: Request, res: Response) => {
  try {
    const id = req.params.id as string;
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// PUT /books/:id — update a book
app.put('/books/:id', (req: Request, res: Response) => {
  try {
    const id = req.params.id as string;
    const { title, author, year, isbn } = req.body;

    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    const updates: string[] = [];
    const values: (string | number | null)[] = [];

    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    if (author !== undefined) {
      updates.push('author = ?');
      values.push(author);
    }
    if (year !== undefined) {
      updates.push('year = ?');
      values.push(year);
    }
    if (isbn !== undefined) {
      updates.push('isbn = ?');
      values.push(isbn);
    }

    if (updates.length === 0) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(id);
    db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`).run(...values);

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    res.status(200).json(book);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/:id — delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  try {
    const id = req.params.id as string;
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    res.status(204).send();
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export { app, server };
