import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

type BookInput = Omit<Book, 'id'>;
type AppOptions = { databasePath?: string; database?: DatabaseSync };

function json(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const data = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += data.length;
    if (size > 1_000_000) throw Object.assign(new Error('Request body is too large'), { status: 413 });
    chunks.push(data);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw Object.assign(new Error('Request body must be valid JSON'), { status: 400 }); }
}

function validateBook(value: unknown): BookInput | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const input = value as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim() ||
      typeof input.author !== 'string' || !input.author.trim()) return null;
  if (typeof input.year !== 'number' || !Number.isInteger(input.year) || input.year < 0 || input.year > 9999) return null;
  if (typeof input.isbn !== 'string' || !input.isbn.trim()) return null;
  return { title: input.title.trim(), author: input.author.trim(), year: input.year, isbn: input.isbn.trim() };
}

export function createApp(options: AppOptions = {}): { server: Server; close: () => void } {
  let db = options.database;
  let ownsDatabase = false;
  if (!db) {
    const path = resolve(options.databasePath ?? process.env.DATABASE_PATH ?? 'data/books.sqlite');
    mkdirSync(dirname(path), { recursive: true });
    db = new DatabaseSync(path);
    ownsDatabase = true;
  }
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
    year INTEGER NOT NULL, isbn TEXT NOT NULL
  ); CREATE INDEX IF NOT EXISTS books_author_idx ON books(author);`);

  const server = createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const path = url.pathname;
    try {
      if (req.method === 'GET' && path === '/health') return json(res, 200, { status: 'ok' });
      if (req.method === 'GET' && path === '/books') {
        const author = url.searchParams.get('author');
        const rows = author
          ? db!.prepare('SELECT * FROM books WHERE author = ? ORDER BY rowid').all(author)
          : db!.prepare('SELECT * FROM books ORDER BY rowid').all();
        return json(res, 200, rows);
      }
      if (req.method === 'POST' && path === '/books') {
        const book = validateBook(await readJson(req));
        if (!book) return json(res, 400, { error: 'title, author, year, and isbn are required; year must be a non-negative integer' });
        const record: Book = { id: randomUUID(), ...book };
        db!.prepare('INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)')
          .run(record.id, record.title, record.author, record.year, record.isbn);
        return json(res, 201, record);
      }
      const match = path.match(/^\/books\/([^/]+)$/);
      if (match && (req.method === 'GET' || req.method === 'PUT' || req.method === 'DELETE')) {
        const id = decodeURIComponent(match[1]!);
        if (req.method === 'GET') {
          const book = db!.prepare('SELECT * FROM books WHERE id = ?').get(id);
          return book ? json(res, 200, book) : json(res, 404, { error: 'Book not found' });
        }
        if (req.method === 'DELETE') {
          const result = db!.prepare('DELETE FROM books WHERE id = ?').run(id);
          return result.changes ? json(res, 200, { message: 'Book deleted' }) : json(res, 404, { error: 'Book not found' });
        }
        const book = validateBook(await readJson(req));
        if (!book) return json(res, 400, { error: 'title, author, year, and isbn are required; year must be a non-negative integer' });
        const result = db!.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
          .run(book.title, book.author, book.year, book.isbn, id);
        if (!result.changes) return json(res, 404, { error: 'Book not found' });
        return json(res, 200, { id, ...book });
      }
      return json(res, 404, { error: 'Route not found' });
    } catch (error) {
      const status = typeof error === 'object' && error !== null && 'status' in error ? Number(error.status) : 500;
      if (status >= 400 && status < 500) return json(res, status, { error: (error as Error).message });
      console.error(error);
      return json(res, 500, { error: 'Internal server error' });
    }
  });
  return { server, close: () => { server.close(); if (ownsDatabase) db!.close(); } };
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  const port = Number(process.env.PORT ?? 3000);
  const app = createApp();
  app.server.listen(port, () => console.log(`Book API listening on http://localhost:${port}`));
}
