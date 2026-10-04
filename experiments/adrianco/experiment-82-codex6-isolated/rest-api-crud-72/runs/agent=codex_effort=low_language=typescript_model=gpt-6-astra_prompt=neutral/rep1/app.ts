import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

function json(res: ServerResponse, status: number, value: unknown): void {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(value));
}

async function readBook(req: IncomingMessage): Promise<BookInput> {
  if (req.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    throw new HttpError(415, 'Content-Type must be application/json');
  }
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 64 * 1024) throw new HttpError(413, 'Request body exceeds 64 KiB');
    chunks.push(Buffer.from(chunk));
  }
  let value: unknown;
  try { value = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new HttpError(400, 'Invalid JSON body'); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new HttpError(400, 'Body must be a JSON object');
  }
  const body = value as Record<string, unknown>;
  for (const field of ['title', 'author']) {
    if (typeof body[field] !== 'string' || !body[field].trim()) {
      throw new HttpError(400, `${field} is required and must be a non-empty string`);
    }
  }
  if (body.year != null && (typeof body.year !== 'number' || !Number.isSafeInteger(body.year))) {
    throw new HttpError(400, 'year must be an integer or null');
  }
  if (body.isbn != null && (typeof body.isbn !== 'string' || !body.isbn.trim())) {
    throw new HttpError(400, 'isbn must be a non-empty string or null');
  }
  return {
    title: (body.title as string).trim(), author: (body.author as string).trim(),
    year: (body.year as number | null | undefined) ?? null,
    isbn: typeof body.isbn === 'string' ? body.isbn.trim() : null,
  };
}

/** Each instance owns its database; closing the server closes the database. */
export function createApp(databasePath = 'books.sqlite') {
  const db = new DatabaseSync(databasePath);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL CHECK(length(trim(title)) > 0),
      author TEXT NOT NULL CHECK(length(trim(author)) > 0),
      year INTEGER,
      isbn TEXT
    );
  `);
  const get = db.prepare('SELECT * FROM books WHERE id = ?');
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const path = url.pathname;
      if (path === '/health' && req.method === 'GET') {
        db.prepare('SELECT 1').get();
        return json(res, 200, { status: 'ok' });
      }
      if (path === '/books') {
        if (req.method === 'GET') {
          const author = url.searchParams.get('author');
          const books = author === null
            ? db.prepare('SELECT * FROM books ORDER BY id').all()
            : db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author);
          return json(res, 200, books);
        }
        if (req.method === 'POST') {
          const book = await readBook(req);
          const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
            .run(book.title, book.author, book.year, book.isbn);
          res.setHeader('Location', `/books/${result.lastInsertRowid}`);
          return json(res, 201, get.get(result.lastInsertRowid));
        }
        res.setHeader('Allow', 'GET, POST');
        throw new HttpError(405, 'Method not allowed');
      }
      const match = /^\/books\/([^/]+)$/.exec(path);
      if (match) {
        if (!/^[1-9]\d*$/.test(match[1]) || !Number.isSafeInteger(Number(match[1]))) {
          throw new HttpError(400, 'Book ID must be a positive integer');
        }
        const id = Number(match[1]);
        if (!['GET', 'PUT', 'DELETE'].includes(req.method ?? '')) {
          res.setHeader('Allow', 'GET, PUT, DELETE');
          throw new HttpError(405, 'Method not allowed');
        }
        if (!get.get(id)) throw new HttpError(404, 'Book not found');
        if (req.method === 'GET') return json(res, 200, get.get(id));
        if (req.method === 'PUT') {
          const book = await readBook(req);
          const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
            .run(book.title, book.author, book.year, book.isbn, id);
          if (!result.changes) throw new HttpError(404, 'Book not found');
          return json(res, 200, get.get(id));
        }
        db.prepare('DELETE FROM books WHERE id = ?').run(id);
        return json(res, 200, { deleted: true, id });
      }
      throw new HttpError(404, 'Route not found');
    } catch (error) {
      if (error instanceof HttpError) json(res, error.status, { error: error.message });
      else {
        console.error(error);
        json(res, 500, { error: 'Internal server error' });
      }
    }
  });
  server.on('close', () => db.close());
  return server;
}
