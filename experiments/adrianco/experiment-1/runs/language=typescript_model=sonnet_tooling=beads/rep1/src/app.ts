import express, { Request, Response, NextFunction } from 'express';
import Database from 'better-sqlite3';
import { Book } from './db';

export function createApp(db: Database.Database): express.Application {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok' });
  });

  // POST /books — Create a book
  app.post('/books', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body as Partial<Book>;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'author is required' });
    }

    const stmt = db.prepare(
      `INSERT INTO books (title, author, year, isbn)
       VALUES (?, ?, ?, ?)`,
    );
    const result = stmt.run(title.trim(), author.trim(), year ?? null, isbn ?? null);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    return res.status(201).json(book);
  });

  // GET /books — List books (optional ?author= filter)
  app.get('/books', (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (author && typeof author === 'string') {
      books = db
        .prepare('SELECT * FROM books WHERE author LIKE ? ORDER BY id')
        .all(`%${author}%`) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }
    return res.json(books);
  });

  // GET /books/:id — Get a single book
  app.get('/books/:id', (req: Request, res: Response) => {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    return res.json(book);
  });

  // PUT /books/:id — Update a book
  app.put('/books/:id', (req: Request, res: Response) => {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }

    const { title, author, year, isbn } = req.body as Partial<Book>;

    const newTitle = title !== undefined ? title : existing.title;
    const newAuthor = author !== undefined ? author : existing.author;

    if (typeof newTitle !== 'string' || newTitle.trim() === '') {
      return res.status(400).json({ error: 'title must be a non-empty string' });
    }
    if (typeof newAuthor !== 'string' || newAuthor.trim() === '') {
      return res.status(400).json({ error: 'author must be a non-empty string' });
    }

    db.prepare(
      `UPDATE books
       SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now')
       WHERE id = ?`,
    ).run(
      newTitle.trim(),
      newAuthor.trim(),
      year !== undefined ? year : existing.year,
      isbn !== undefined ? isbn : existing.isbn,
      req.params.id,
    );

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book;
    return res.json(book);
  });

  // DELETE /books/:id — Delete a book
  app.delete('/books/:id', (req: Request, res: Response) => {
    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'Book not found' });
    }
    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);
    return res.status(204).send();
  });

  // Generic error handler
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}
