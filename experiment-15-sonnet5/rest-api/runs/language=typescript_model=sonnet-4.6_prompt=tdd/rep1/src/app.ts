import express, { Request, Response } from 'express';
import Database from 'better-sqlite3';

interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function initDb(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
}

export function buildApp(db: Database.Database): express.Application {
  initDb(db);
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body as Partial<Book>;
    if (!title || !author) {
      res.status(400).json({ error: 'title and author are required' });
      return;
    }
    const result = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title, author, year ?? null, isbn ?? null);
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(result.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const { author } = req.query as { author?: string };
    let books: Book[];
    if (author) {
      books = db.prepare('SELECT * FROM books WHERE author = ?').all(author) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books').all() as Book[];
    }
    res.json(books);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(Number(req.params.id)) as Book | undefined;
    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    res.json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body as Partial<Book>;
    if (!title || !author) {
      res.status(400).json({ error: 'title and author are required' });
      return;
    }
    const existing = db
      .prepare('SELECT id FROM books WHERE id = ?')
      .get(Number(req.params.id));
    if (!existing) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      title,
      author,
      year ?? null,
      isbn ?? null,
      Number(req.params.id)
    );
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(Number(req.params.id)) as Book;
    res.json(book);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const existing = db
      .prepare('SELECT id FROM books WHERE id = ?')
      .get(Number(req.params.id));
    if (!existing) {
      res.status(404).json({ error: 'book not found' });
      return;
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
    res.status(204).send();
  });

  return app;
}
