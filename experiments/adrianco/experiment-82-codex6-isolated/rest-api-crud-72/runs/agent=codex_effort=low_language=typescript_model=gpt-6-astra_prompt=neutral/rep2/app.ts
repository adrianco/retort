import express, { type ErrorRequestHandler } from 'express';
import { DatabaseSync } from 'node:sqlite';

interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function validate(value: unknown): BookInput {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Body must be a JSON object');
  }
  const data = value as Record<string, unknown>;
  for (const field of ['title', 'author']) {
    if (typeof data[field] !== 'string' || !data[field].trim()) {
      throw new Error(`${field} is required and must be a non-empty string`);
    }
  }
  if (data.year != null && (typeof data.year !== 'number' || !Number.isSafeInteger(data.year))) {
    throw new Error('year must be an integer or null');
  }
  if (data.isbn != null && (typeof data.isbn !== 'string' || !data.isbn.trim())) {
    throw new Error('isbn must be a non-empty string or null');
  }
  return {
    title: (data.title as string).trim(),
    author: (data.author as string).trim(),
    year: (data.year as number | null | undefined) ?? null,
    isbn: typeof data.isbn === 'string' ? data.isbn.trim() : null,
  };
}

/** Each instance owns its database; callers close it after stopping the server. */
export function createApp(databasePath = 'books.sqlite') {
  const db = new DatabaseSync(databasePath);
  db.exec(`
    PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL CHECK(length(trim(title)) > 0),
      author TEXT NOT NULL CHECK(length(trim(author)) > 0),
      year INTEGER,
      isbn TEXT
    );
    CREATE INDEX IF NOT EXISTS books_author ON books(author);
  `);
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
      res.status(400).json({ error: 'author filter must be a single string' });
      return;
    }
    res.json(author === undefined
      ? db.prepare('SELECT * FROM books ORDER BY id').all()
      : db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author));
  });

  app.post('/books', (req, res) => {
    let book: BookInput;
    try { book = validate(req.body); }
    catch (error) { res.status(400).json({ error: (error as Error).message }); return; }
    const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(book.title, book.author, book.year, book.isbn);
    const created = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    res.location(`/books/${result.lastInsertRowid}`).status(201).json(created);
  });

  app.param('id', (req, res, next, id: string) => {
    if (!/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id))) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
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
    let book: BookInput;
    try { book = validate(req.body); }
    catch (error) { res.status(400).json({ error: (error as Error).message }); return; }
    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(book.title, book.author, book.year, book.isbn, id);
    res.json(db.prepare('SELECT * FROM books WHERE id = ?').get(id));
  });

  app.delete('/books/:id', (req, res) => {
    const result = db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
    if (!result.changes) { res.status(404).json({ error: 'Book not found' }); return; }
    res.status(200).json({ message: 'Book deleted' });
  });

  app.use((_req, res) => { res.status(404).json({ error: 'Route not found' }); });
  const errorHandler: ErrorRequestHandler = (error, _req, res, _next) => {
    if (error.type === 'entity.too.large') {
      res.status(413).json({ error: 'Request body too large' });
    } else if (error instanceof SyntaxError || error.status === 400) {
      res.status(400).json({ error: 'Invalid JSON body' });
    } else if (error.status === 415) {
      res.status(415).json({ error: 'Unsupported request encoding' });
    } else {
      console.error(error);
      res.status(500).json({ error: 'Internal server error' });
    }
  };
  app.use(errorHandler);
  return { app, close: () => db.close() };
}
