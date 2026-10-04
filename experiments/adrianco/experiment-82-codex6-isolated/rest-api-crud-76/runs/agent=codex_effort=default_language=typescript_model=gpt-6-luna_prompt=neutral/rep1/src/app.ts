import express, { type NextFunction, type Request, type Response } from 'express';
import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Omit<Book, 'id'>;

export function createApp(database: Database.Database = new Database(process.env.DATABASE_PATH ?? 'books.db')) {
  database.pragma('foreign_keys = ON');
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
    const input = parseBookInput(req.body);
    if (!input) return res.status(400).json({ error: 'title and author are required; year must be an integer and isbn a string' });
    const result = database.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title, input.author, input.year, input.isbn);
    return res.status(201).json(findBook(database, Number(result.lastInsertRowid)));
  });

  app.get('/books', (req, res) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = author === undefined
      ? database.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id').all()
      : database.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id').all(author);
    return res.status(200).json(books);
  });

  app.get('/books/:id', (req, res) => {
    const book = findBook(database, parseId(req.params.id));
    return book ? res.status(200).json(book) : res.status(404).json({ error: 'Book not found' });
  });

  app.put('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: 'Invalid book id' });
    const input = parseBookInput(req.body);
    if (!input) return res.status(400).json({ error: 'title and author are required; year must be an integer and isbn a string' });
    const result = database.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(input.title, input.author, input.year, input.isbn, id);
    const book = findBook(database, id);
    return result.changes ? res.status(200).json(book) : res.status(404).json({ error: 'Book not found' });
  });

  app.delete('/books/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: 'Invalid book id' });
    const result = database.prepare('DELETE FROM books WHERE id = ?').run(id);
    return result.changes ? res.status(204).end() : res.status(404).json({ error: 'Book not found' });
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError) return res.status(400).json({ error: 'Invalid JSON body' });
    return res.status(500).json({ error: 'Internal server error' });
  });
  return app;
}

function parseBookInput(body: unknown): BookInput | null {
  if (!body || typeof body !== 'object') return null;
  const value = body as Record<string, unknown>;
  if (typeof value.title !== 'string' || !value.title.trim() || typeof value.author !== 'string' || !value.author.trim()) return null;
  if (value.year !== undefined && value.year !== null && (!Number.isInteger(value.year) || typeof value.year !== 'number')) return null;
  if (value.isbn !== undefined && value.isbn !== null && typeof value.isbn !== 'string') return null;
  return {
    title: value.title.trim(),
    author: value.author.trim(),
    year: (value.year as number | null | undefined) ?? null,
    isbn: (value.isbn as string | null | undefined)?.trim() || null,
  };
}

function parseId(raw: string): number {
  return /^\d+$/.test(raw) ? Number(raw) : NaN;
}

function findBook(database: Database.Database, id: number): Book | undefined {
  return database.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?').get(id) as Book | undefined;
}
