import express, { type ErrorRequestHandler } from 'express';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function validateBook(value: unknown): Omit<Book, 'id'> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Body must be a JSON object');
  }
  const { title, author, year, isbn } = value as Record<string, unknown>;
  if (typeof title !== 'string' || !title.trim()) throw new Error('title is required');
  if (typeof author !== 'string' || !author.trim()) throw new Error('author is required');
  if (year != null && (typeof year !== 'number' || !Number.isSafeInteger(year))) {
    throw new Error('year must be an integer or null');
  }
  if (isbn != null && (typeof isbn !== 'string' || !isbn.trim())) {
    throw new Error('isbn must be a nonempty string or null');
  }
  return { title: title.trim(), author: author.trim(), year: year as number ?? null,
    isbn: typeof isbn === 'string' ? isbn.trim() : null };
}

export function createApp(databasePath = 'books.sqlite') {
  const db = new DatabaseSync(databasePath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    author TEXT NOT NULL CHECK(length(trim(author)) > 0),
    year INTEGER,
    isbn TEXT
  )`);
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '100kb' }));
  app.get('/health', (_req, res) => {
    db.prepare('SELECT 1').get();
    res.json({ status: 'ok' });
  });
  app.get('/books', (req, res) => {
    const author = req.query.author;
    if (author !== undefined && typeof author !== 'string') {
      res.status(400).json({ error: 'author filter must be a string' });
      return;
    }
    const books = author === undefined
      ? db.prepare('SELECT * FROM books ORDER BY id').all()
      : db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author);
    res.json(books);
  });
  app.post('/books', (req, res) => {
    let book;
    try { book = validateBook(req.body); }
    catch (error) { res.status(400).json({ error: (error as Error).message }); return; }
    const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(book.title, book.author, book.year, book.isbn);
    const id = Number(result.lastInsertRowid);
    res.status(201).location(`/books/${id}`).json({ id, ...book });
  });
  app.param('id', (req, res, next, raw: string) => {
    if (!/^[1-9]\d*$/.test(raw) || !Number.isSafeInteger(Number(raw))) {
      res.status(400).json({ error: 'id must be a positive integer' }); return;
    }
    next();
  });
  app.get('/books/:id', (req, res) => {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
    if (!book) { res.status(404).json({ error: 'Book not found' }); return; }
    res.json(book);
  });
  app.put('/books/:id', (req, res) => {
    const id = Number(req.params.id);
    if (!db.prepare('SELECT id FROM books WHERE id = ?').get(id)) {
      res.status(404).json({ error: 'Book not found' }); return;
    }
    let book;
    try { book = validateBook(req.body); }
    catch (error) { res.status(400).json({ error: (error as Error).message }); return; }
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(book.title, book.author, book.year, book.isbn, id);
    res.json({ id, ...book });
  });
  app.delete('/books/:id', (req, res) => {
    const result = db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
    if (!result.changes) { res.status(404).json({ error: 'Book not found' }); return; }
    res.json({ message: 'Book deleted' });
  });
  app.use((_req, res) => { res.status(404).json({ error: 'Route not found' }); });
  const onError: ErrorRequestHandler = (error, _req, res, _next) => {
    const status = typeof error.status === 'number' && error.status >= 400 && error.status < 500
      ? error.status : 500;
    res.status(status).json({ error: status === 500 ? 'Internal server error'
      : status === 413 ? 'Request body too large' : 'Invalid JSON request' });
  };
  app.use(onError);
  return { app, close: () => db.close() };
}
