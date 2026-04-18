import express, { Request, Response } from 'express';
import type { Database } from 'better-sqlite3';
import { Book } from './db';

export function createApp(db: Database) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body ?? {};
    if (typeof title !== 'string' || !title.trim()) {
      return res.status(400).json({ error: 'title is required' });
    }
    if (typeof author !== 'string' || !author.trim()) {
      return res.status(400).json({ error: 'author is required' });
    }
    if (year !== undefined && year !== null && typeof year !== 'number') {
      return res.status(400).json({ error: 'year must be a number' });
    }
    if (isbn !== undefined && isbn !== null && typeof isbn !== 'string') {
      return res.status(400).json({ error: 'isbn must be a string' });
    }
    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(title, author, year ?? null, isbn ?? null);
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(info.lastInsertRowid) as Book;
    return res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const author = req.query.author;
    let rows: Book[];
    if (typeof author === 'string' && author.length > 0) {
      rows = db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    } else {
      rows = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }
    return res.status(200).json(rows);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as
      | Book
      | undefined;
    if (!book) return res.status(404).json({ error: 'book not found' });
    return res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as
      | Book
      | undefined;
    if (!existing) return res.status(404).json({ error: 'book not found' });

    const { title, author, year, isbn } = req.body ?? {};
    if (typeof title !== 'string' || !title.trim()) {
      return res.status(400).json({ error: 'title is required' });
    }
    if (typeof author !== 'string' || !author.trim()) {
      return res.status(400).json({ error: 'author is required' });
    }
    if (year !== undefined && year !== null && typeof year !== 'number') {
      return res.status(400).json({ error: 'year must be a number' });
    }
    if (isbn !== undefined && isbn !== null && typeof isbn !== 'string') {
      return res.status(400).json({ error: 'isbn must be a string' });
    }
    db.prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    ).run(title, author, year ?? null, isbn ?? null, id);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    return res.status(200).json(book);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }
    const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
    if (info.changes === 0)
      return res.status(404).json({ error: 'book not found' });
    return res.status(204).send();
  });

  return app;
}
