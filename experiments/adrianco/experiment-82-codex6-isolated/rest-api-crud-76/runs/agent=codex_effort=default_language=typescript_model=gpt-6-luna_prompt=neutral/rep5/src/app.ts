import express, { type NextFunction, type Request, type Response } from 'express';
import type { DatabaseSync } from 'node:sqlite';
import type { Book } from './db.js';

type BookInput = Pick<Book, 'title' | 'author'> & Partial<Pick<Book, 'year' | 'isbn'>>;

function validateBook(body: unknown): { value?: BookInput; error?: string } {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return { error: 'Request body must be a JSON object' };
  const input = body as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim()) return { error: 'title is required' };
  if (typeof input.author !== 'string' || !input.author.trim()) return { error: 'author is required' };
  if (input.year !== undefined && input.year !== null && (!Number.isInteger(input.year) || (input.year as number) < 0)) {
    return { error: 'year must be a non-negative integer or null' };
  }
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') return { error: 'isbn must be a string or null' };
  return { value: {
    title: input.title.trim(),
    author: input.author.trim(),
    year: input.year as number | null | undefined,
    isbn: typeof input.isbn === 'string' ? input.isbn.trim() : input.isbn as null | undefined
  } };
}

export function createApp(db: DatabaseSync) {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => res.status(200).json({ status: 'ok' }));

  app.post('/books', (req, res) => {
    const parsed = validateBook(req.body);
    if (parsed.error) return res.status(400).json({ error: parsed.error });
    const book = parsed.value!;
    const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(book.title, book.author, book.year ?? null, book.isbn ?? null);
    const created = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(result.lastInsertRowid)) as unknown as Book;
    return res.status(201).json(created);
  });

  app.get('/books', (req, res) => {
    const author = typeof req.query.author === 'string' ? req.query.author : undefined;
    const books = author !== undefined
      ? db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author) as unknown as Book[]
      : db.prepare('SELECT * FROM books ORDER BY id').all() as unknown as Book[];
    return res.status(200).json(books);
  });

  app.get('/books/:id', (req, res) => {
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id)) as unknown as Book | undefined;
    if (!book) return res.status(404).json({ error: 'Book not found' });
    return res.status(200).json(book);
  });

  app.put('/books/:id', (req, res) => {
    const parsed = validateBook(req.body);
    if (parsed.error) return res.status(400).json({ error: parsed.error });
    const book = parsed.value!;
    const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(book.title, book.author, book.year ?? null, book.isbn ?? null, Number(req.params.id));
    if (result.changes === 0) return res.status(404).json({ error: 'Book not found' });
    return res.status(200).json(db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id)));
  });

  app.delete('/books/:id', (req, res) => {
    const result = db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
    if (result.changes === 0) return res.status(404).json({ error: 'Book not found' });
    return res.status(204).end();
  });

  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof SyntaxError && 'body' in err) return res.status(400).json({ error: 'Invalid JSON body' });
    return res.status(500).json({ error: 'Internal server error' });
  });
  return app;
}
