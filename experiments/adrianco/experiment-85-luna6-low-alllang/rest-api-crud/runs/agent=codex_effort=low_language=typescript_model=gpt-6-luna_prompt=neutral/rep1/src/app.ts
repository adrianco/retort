import express, { type NextFunction, type Request, type Response } from 'express';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function validateBook(body: unknown): { value?: BookInput; error?: string } {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'Request body must be a JSON object' };
  }
  const input = body as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim()) return { error: 'title is required' };
  if (typeof input.author !== 'string' || !input.author.trim()) return { error: 'author is required' };
  if (input.year !== undefined && input.year !== null && (!Number.isInteger(input.year) || typeof input.year !== 'number')) {
    return { error: 'year must be an integer or null' };
  }
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') {
    return { error: 'isbn must be a string or null' };
  }
  return {
    value: {
      title: input.title.trim(),
      author: input.author.trim(),
      year: input.year === undefined ? null : input.year as number | null,
      isbn: input.isbn === undefined ? null : input.isbn as string | null,
    },
  };
}

export function createApp(database: DatabaseSync = new DatabaseSync('books.sqlite')) {
  database.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const app = express();
  app.use(express.json());
  app.get('/health', (_req, res) => res.status(200).json({ status: 'ok' }));

  app.post('/books', (req, res) => {
    const { value, error } = validateBook(req.body);
    if (error || !value) return res.status(400).json({ error });
    const result = database.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(value.title, value.author, value.year, value.isbn);
    const book = database.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as unknown as Book;
    return res.status(201).json(book);
  });

  app.get('/books', (req, res) => {
    const author = typeof req.query.author === 'string' ? req.query.author.trim() : '';
    const books = author
      ? database.prepare('SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id').all(author)
      : database.prepare('SELECT * FROM books ORDER BY id').all();
    return res.status(200).json(books);
  });

  app.get('/books/:id', (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: 'id must be a positive integer' });
    const book = database.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) return res.status(404).json({ error: 'Book not found' });
    return res.status(200).json(book);
  });

  app.put('/books/:id', (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: 'id must be a positive integer' });
    const { value, error } = validateBook(req.body);
    if (error || !value) return res.status(400).json({ error });
    const result = database.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(value.title, value.author, value.year, value.isbn, id);
    if (result.changes === 0) return res.status(404).json({ error: 'Book not found' });
    return res.status(200).json(database.prepare('SELECT * FROM books WHERE id = ?').get(id));
  });

  app.delete('/books/:id', (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: 'id must be a positive integer' });
    const result = database.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (result.changes === 0) return res.status(404).json({ error: 'Book not found' });
    return res.status(204).end();
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError) return res.status(400).json({ error: 'Invalid JSON body' });
    return res.status(500).json({ error: 'Internal server error' });
  });
  return app;
}
