import express, { Request, Response, NextFunction } from 'express';
import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

let db: Database.Database;

export function setDb(database: Database.Database) {
  db = database;
}

export function getDb(): Database.Database {
  return db;
}

const app = express();
app.use(express.json());

app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year || null, isbn || null);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
  res.status(201).json(book);
});

app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;

  if (author) {
    const books = db.prepare('SELECT * FROM books WHERE author = ?').all(author as string) as Book[];
    return res.json(books);
  }

  const books = db.prepare('SELECT * FROM books').all() as Book[];
  res.json(books);
});

app.get('/books/:id', (req: Request, res: Response) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.json(book);
});

app.put('/books/:id', (req: Request, res: Response) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }

  db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  ).run(title, author, year || null, isbn || null, req.params.id);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book;
  res.json(book);
});

app.delete('/books/:id', (req: Request, res: Response) => {
  const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;

  if (!existing) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
  res.status(204).send();
});

app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

export { app };
