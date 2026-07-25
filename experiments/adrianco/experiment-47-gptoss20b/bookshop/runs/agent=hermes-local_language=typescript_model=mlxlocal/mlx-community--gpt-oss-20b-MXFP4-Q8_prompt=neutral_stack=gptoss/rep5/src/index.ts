import express, { Request, Response } from 'express';
import { body, query, param, validationResult } from 'express-validator';
import { runAsync, getAsync, allAsync } from './database';
import { Book } from './types';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => res.status(200).json({ status: 'ok' }));

// Create book
app.post('/books',
  body('title').isString().notEmpty(),
  body('author').isString().notEmpty(),
  body('year').optional().isInt({ min: 0 }),
  body('isbn').optional().isString(),
  async (_req: Request, res: Response) => {
    const errors = validationResult(_req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { title, author, year, isbn } = _req.body as Book;
    const insertResult: any = await runAsync(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, [title, author, year, isbn]);
    const book = await getAsync(`SELECT * FROM books WHERE id = ?`, [insertResult.lastID]);
    res.status(201).json(book);
  }
);

// List books
app.get('/books',
  query('author').optional().isString(),
  async (_req: Request, res: Response) => {
    const { author } = _req.query as any;
    let sql = 'SELECT * FROM books';
    const params: any[] = [];
    if (author) {
      sql += ' WHERE author = ?';
      params.push(author);
    }
    const books = await allAsync(sql, params);
    res.json(books);
  }
);

// Get single book
app.get('/books/:id',
  param('id').isInt(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const book = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!book) return res.status(404).json({ error: 'Not found' });
    res.json(book);
  }
);

// Update book
app.put('/books/:id',
  param('id').isInt(),
  body('title').optional().isString(),
  body('author').optional().isString(),
  body('year').optional().isInt({ min: 0 }),
  body('isbn').optional().isString(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const existing = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) return res.status(404).json({ error: 'Not found' });
    const { title, author, year, isbn } = _req.body as Book;
    const updated = {
      title: title ?? existing.title,
      author: author ?? existing.author,
      year: year ?? existing.year,
      isbn: isbn ?? existing.isbn,
    };
    await runAsync(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, [updated.title, updated.author, updated.year, updated.isbn, id]);
    const book = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    res.json(book);
  }
);

// Delete book
app.delete('/books/:id',
  param('id').isInt(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const existing = await getAsync('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) return res.status(404).json({ error: 'Not found' });
    await runAsync('DELETE FROM books WHERE id = ?', [id]);
    res.status(204).send();
  }
);

export default app;

// Start server if run directly
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  initDb().then(() => {
    app.listen(PORT, () => console.log(`Server running on ${PORT}`));
  });
}
app.use(express.json());

// Health check
app.get('/health', (_req: Request, res: Response) => res.status(200).json({ status: 'ok' }));

// Create book
app.post(
  '/books',
  body('title').isString().notEmpty(),
  body('author').isString().notEmpty(),
  body('year').optional().isInt({ min: 0 }),
  body('isbn').optional().isString(),
  async (_req: Request, res: Response) => {
    const errors = validationResult(_req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { title, author, year, isbn } = _req.body as Book;
    // @ts-ignore
const insertResult = await new Promise<{lastID: number}>(resolve => {
        db.run(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, [title, author, year, isbn], function(err) {
            if (err) throw err;
            resolve({ lastID: this.lastID });
        });
    });
// @ts-ignore
const book = await db.get(`SELECT * FROM books WHERE id = ?`, [insertResult.lastID]);

  }
);

// List books
app.get(
  '/books',
  query('author').optional().isString(),
  async (_req: Request, res: Response) => {
    const { author } = _req.query as any;
    let sql = 'SELECT * FROM books';
    const params: any[] = [];
    if (author) {
      sql += ' WHERE author = ?';
      params.push(author);
    }
    const books = await db.all(sql, params);
    res.json(books);
  }
);

// Get single
app.get(
  '/books/:id',
  param('id').isInt(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    if (!book) return res.status(404).json({ error: 'Not found' });
    res.json(book);
  }
);

// Update
app.put(
  '/books/:id',
  param('id').isInt(),
  body('title').optional().isString(),
  body('author').optional().isString(),
  body('year').optional().isInt({ min: 0 }),
  body('isbn').optional().isString(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const existing = await db.get('SELECT * FROM books WHERE id = ?', [id]) as any;
    if (!existing) return res.status(404).json({ error: 'Not found' });
    const { title, author, year, isbn } = _req.body as Book;
    const updated = {
      title: title ?? existing.title,
      author: author ?? existing.author,
      year: year ?? existing.year,
      isbn: isbn ?? existing.isbn,
    };
    await db.run(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`, [updated.title, updated.author, updated.year, updated.isbn, id]);
    // @ts-ignore
const book = await db.get(`SELECT * FROM books WHERE id = ?`, [id]) as any;
    res.json(book);
  }
 );

// Delete
app.delete(
  '/books/:id',
  param('id').isInt(),
  async (_req: Request, res: Response) => {
    const id = parseInt(_req.params.id);
    const existing = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) return res.status(404).json({ error: 'Not found' });
    await db.run('DELETE FROM books WHERE id = ?', [id]);
    res.status(204).send();
  }
);

export default app;

// Start server if run directly
if (require.main === module) {
  const PORT = process.env.PORT || 3000;
  initDb().then(() => {
    app.listen(PORT, () => console.log(`Server running on ${PORT}`));
  });
}
