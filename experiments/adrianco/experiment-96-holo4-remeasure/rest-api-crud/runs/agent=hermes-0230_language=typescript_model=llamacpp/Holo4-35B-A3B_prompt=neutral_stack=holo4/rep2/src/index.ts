import express, { Request, Response } from 'express';
import { run, all, get, runWithLastInsertId } from './db';
import { Book, CreateBookInput, UpdateBookInput } from './types';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'OK' });
});

// Create a new book
app.post('/books', async (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  if (!year || !isbn) {
    return res.status(400).json({ error: 'Year and ISBN are required' });
  }

  try {
    const result = await runWithLastInsertId(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    const book = await get<Book>(
      'SELECT * FROM books WHERE id = ?',
      [result.lastInsertId]
    );
    res.status(201).json(book);
  } catch (err: any) {
    if (err.message?.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// List all books (with optional author filter)
app.get('/books', async (req: Request, res: Response) => {
  const { author } = req.query;

  try {
    let books: Book[];
    if (author) {
      books = await all<Book>('SELECT * FROM books WHERE author = ?', [author as string]);
    } else {
      books = await all<Book>('SELECT * FROM books');
    }
    res.json(books);
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response) => {
  try {
    const book = await get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book
app.put('/books/:id', async (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  const id = req.params.id;

  try {
    const existing = await get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    const updates: string[] = [];
    const values: any[] = [];

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
    await run(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`, values);
    const book = await get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    res.json(book);
  } catch (err: any) {
    if (err.message?.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
app.delete('/books/:id', async (req: Request, res: Response) => {
  try {
    const existing = await get<Book>('SELECT * FROM books WHERE id = ?', [req.params.id]);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    await run('DELETE FROM books WHERE id = ?', [req.params.id]);
    res.status(204).send();
  } catch {
    res.status(500).json({ error: 'Internal server error' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export default app;
