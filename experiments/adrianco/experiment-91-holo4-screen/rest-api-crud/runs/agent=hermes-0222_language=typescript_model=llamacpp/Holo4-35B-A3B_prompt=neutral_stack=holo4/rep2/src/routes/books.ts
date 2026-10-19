import { Router, Request, Response } from 'express';
import { getDb } from '../db';
import { Book, CreateBookInput, UpdateBookInput, validateCreateBook, validateUpdateBook } from '../validation';

const router = Router();

function bookRow(row: any): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
  };
}

// GET /books - List all books (support ?author= filter)
router.get('/', (req: Request, res: Response) => {
  const db = getDb();
  const { author } = req.query;

  let rows: any[];
  if (author && typeof author === 'string' && author.trim() !== '') {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    rows = stmt.all(author);
  } else {
    const stmt = db.prepare('SELECT * FROM books');
    rows = stmt.all();
  }

  res.json(rows.map(bookRow));
});

// POST /books - Create a new book
router.post('/', (req: Request, res: Response) => {
  const db = getDb();
  const body: Partial<CreateBookInput> = req.body;
  const errors = validateCreateBook(body);

  if (errors.length > 0) {
    return res.status(400).json({ error: 'Validation failed', details: errors });
  }

  const input: CreateBookInput = {
    title: body.title!.trim(),
    author: body.author!.trim(),
    year: body.year!,
    isbn: body.isbn!.trim(),
  };

  try {
    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(input.title, input.author, input.year, input.isbn);
    const book = bookRow({ id: result.lastInsertRowid as number, ...input });
    res.status(201).json(book);
  } catch (err: any) {
    if (err.code === 'SQLITE_CONSTRAINT_UNIQUE' || err.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /books/:id - Get a single book by ID
router.get('/:id', (req: Request, res: Response) => {
  const db = getDb();
  const { id } = req.params;
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const book = stmt.get(id);

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(bookRow(book));
});

// PUT /books/:id - Update a book
router.put('/:id', (req: Request, res: Response) => {
  const db = getDb();
  const { id } = req.params;
  const body: Partial<UpdateBookInput> = req.body;
  const errors = validateUpdateBook(body);

  if (errors.length > 0) {
    return res.status(400).json({ error: 'Validation failed', details: errors });
  }

  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as any;
  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const updates: string[] = [];
  const values: any[] = [];

  if (body.title !== undefined) {
    updates.push('title = ?');
    values.push(body.title.trim());
  }
  if (body.author !== undefined) {
    updates.push('author = ?');
    values.push(body.author.trim());
  }
  if (body.year !== undefined) {
    updates.push('year = ?');
    values.push(body.year);
  }
  if (body.isbn !== undefined) {
    updates.push('isbn = ?');
    values.push(body.isbn.trim());
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: 'No valid fields to update' });
  }

  values.push(id);

  try {
    const stmt = db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`);
    stmt.run(...values);
    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    res.json(bookRow(updated));
  } catch (err: any) {
    if (err.message.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'A book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /books/:id - Delete a book
router.delete('/:id', (req: Request, res: Response) => {
  const db = getDb();
  const { id } = req.params;
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  res.status(204).send();
});

export default router;
