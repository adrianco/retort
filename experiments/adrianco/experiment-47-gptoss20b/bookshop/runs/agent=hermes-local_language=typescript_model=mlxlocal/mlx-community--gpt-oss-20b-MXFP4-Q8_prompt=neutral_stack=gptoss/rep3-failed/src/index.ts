import express, { Request, Response } from 'express';
import { body, param, query, validationResult } from 'express-validator';
import { db, init } from './db';
import path from 'path';

const app = express();
app.use(express.json());

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
  (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    const { title, author, year, isbn } = req.body;
    db.data.books.push({ id: Date.now(), title, author, year, isbn });
    await db.write();
    res.status(201).json({ id: db.data.books[db.data.books.length-1].id, title, author, year, isbn });
  }
);

// List books with optional author filter
app.get(
  '/books',
  [query('author').optional().isString()],
  (req: Request, res: Response) => {
    const { author } = req.query;
    let stmt = db.prepare('SELECT * FROM books');
    let params: any[] = [];
    if (author) {
      stmt = db.prepare('SELECT * FROM books WHERE author = ?');
      params = [author];
    }
    const books = stmt.all(...params);
    res.json(books);
  }
);

// Get single book by id
app.get(
  '/books/:id',
  [param('id').isInt()],
  (req: Request, res: Response) => {
    const { id } = req.params;
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
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
  (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    const { id } = req.params;
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    const { title, author, year, isbn } = req.body;
    const stmt = db.prepare(
      'UPDATE books SET title = COALESCE(?, title), author = COALESCE(?, author), year = COALESCE(?, year), isbn = COALESCE(?, isbn) WHERE id = ?'
    );
    stmt.run(title, author, year, isbn, id);
    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    res.json(updated);
  }
);

// Delete book
app.delete(
  '/books/:id',
  [param('id').isInt()],
  (req: Request, res: Response) => {
    const { id } = req.params;
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(id);
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
