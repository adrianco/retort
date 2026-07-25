import express, { Request, Response } from 'express';
import { body, param, query, validationResult } from 'express-validator';
import { db, init } from './db';
import fs from 'fs';
import path from 'path';

// Ensure data directory exists
import express, { Request, Response } from 'express';
import { body, param, query, validationResult } from 'express-validator';
import { db, init } from './db';
import { promisify } from 'util';

const app = express();
app.use(express.json());

const runAsync = promisify(db.run.bind(db));
const getAsync = promisify(db.get.bind(db));
const allAsync = promisify(db.all.bind(db));

// Health endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok' });
});

// Create a new book
app.post(
  '/books',
  [
    body('title').isString().withMessage('title is required'),
    body('author').isString().withMessage('author is required'),
    body('year').optional().isInt({ min: 0 }).withMessage('year must be a positive integer'),
    body('isbn').optional().isString(),
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    const { title, author, year, isbn } = req.body;
    const result = await runAsync('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', [title, author, year ?? null, isbn ?? null]);
    const id = result.lastID;
    res.status(201).json({ id, title, author, year, isbn });
  }
);

// List books with optional author filter
app.get(
  '/books',
  [query('author').optional().isString()],
  async (req: Request, res: Response) => {
    const { author } = req.query;
    let sql = 'SELECT * FROM books';
    const params: any[] = [];
    if (author) {
      sql += ' WHERE author = ?';
      params.push(author as string);
    }
    const books = await allAsync(sql, params);
    res.json(books);
  }
);

// Get single book by id
app.get(
  '/books/:id',
  [param('id').isInt()],
  async (req: Request, res: Response) => {
    const { id } = req.params;
    const book = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.json(book);
  }
);

// Update book
app.put(
  '/books/:id',
  [
    param('id').isInt(),
    body('title').optional().isString(),
    body('author').optional().isString(),
    body('year').optional().isInt({ min: 0 }),
    body('isbn').optional().isString(),
  ],
  async (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    const { id } = req.params;
    const existing = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    const { title, author, year, isbn } = req.body;
    await runAsync(
      'UPDATE books SET title = COALESCE(?, title), author = COALESCE(?, author), year = COALESCE(?, year), isbn = COALESCE(?, isbn) WHERE id = ?',
      [title, author, year ?? null, isbn ?? null, id]
    );
    const updated = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    res.json(updated);
  }
);

// Delete book
app.delete(
  '/books/:id',
  [param('id').isInt()],
  async (req: Request, res: Response) => {
    const { id } = req.params;
    const existing = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    await runAsync('DELETE FROM books WHERE id = ?', [id]);
    res.status(204).send();
  }
);

// Ensure DB is initialized
(async () => {
  await init();
  const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
})();

export default app;
