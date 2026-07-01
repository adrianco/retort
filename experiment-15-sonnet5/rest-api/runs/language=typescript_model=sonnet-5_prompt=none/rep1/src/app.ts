import express, { Express, Request, Response } from 'express';
import { DatabaseSync } from 'node:sqlite';
import { Book } from './types';
import { validateBookInput } from './validation';

export function createApp(db: DatabaseSync): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req: Request, res: Response) => {
    const result = validateBookInput(req.body ?? {});
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const { title, author, year, isbn } = result.data;
    const info = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title as string, author as string, year, isbn);
    const book = db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(info.lastInsertRowid) as unknown as Book;
    res.status(201).json(book);
  });

  app.get('/books', (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (typeof author === 'string') {
      books = db.prepare('SELECT * FROM books WHERE author = ?').all(author) as unknown as Book[];
    } else {
      books = db.prepare('SELECT * FROM books').all() as unknown as Book[];
    }
    res.status(200).json(books);
  });

  app.get('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }
    res.status(200).json(book);
  });

  app.put('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }

    const result = validateBookInput(req.body ?? {}, { partial: true });
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }

    const title = result.data.title ?? existing.title;
    const author = result.data.author ?? existing.author;
    const year = req.body?.year !== undefined ? result.data.year : existing.year;
    const isbn = req.body?.isbn !== undefined ? result.data.isbn : existing.isbn;

    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      title,
      author,
      year,
      isbn,
      id
    );
    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book;
    res.status(200).json(updated);
  });

  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: 'id must be an integer' });
    }
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    res.status(204).send();
  });

  return app;
}
