import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

interface BookInput { title: string; author: string; year: number | null; isbn: string | null }
class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
function validate(value: unknown): BookInput {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new HttpError(400, 'Expected a JSON object');
  const data = value as Record<string, unknown>;
  for (const key of ['title', 'author']) {
    if (typeof data[key] !== 'string' || !data[key].trim()) throw new HttpError(400, `${key} is required and must be a non-empty string`);
  }
  if (data.year != null && (typeof data.year !== 'number' || !Number.isSafeInteger(data.year))) throw new HttpError(400, 'year must be an integer or null');
  if (data.isbn != null && (typeof data.isbn !== 'string' || !data.isbn.trim())) throw new HttpError(400, 'isbn must be a non-empty string or null');
  return { title: (data.title as string).trim(), author: (data.author as string).trim(), year: data.year as number ?? null, isbn: typeof data.isbn === 'string' ? data.isbn.trim() : null };
}
async function readBody(req: IncomingMessage): Promise<unknown> {
  if (req.headers['content-type']?.split(';')[0].trim().toLowerCase() !== 'application/json') throw new HttpError(415, 'Content-Type must be application/json');
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 1_048_576) throw new HttpError(413, 'Request body exceeds 1 MiB');
    chunks.push(Buffer.from(chunk));
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new HttpError(400, 'Invalid JSON body'); }
}
function json(res: ServerResponse, status: number, value: unknown) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(value));
}

export function createApp(databasePath = 'books.sqlite') {
  const db = new DatabaseSync(databasePath);
  db.exec(`PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT
    );`);
  const byId = db.prepare('SELECT * FROM books WHERE id = ?');
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const method = req.method;
      if (url.pathname === '/health' && method === 'GET') {
        db.prepare('SELECT 1').get();
        json(res, 200, { status: 'ok' }); return;
      }
      if (url.pathname === '/books') {
        if (method === 'GET') {
          const author = url.searchParams.get('author');
          json(res, 200, author === null
            ? db.prepare('SELECT * FROM books ORDER BY id').all()
            : db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author));
          return;
        }
        if (method === 'POST') {
          const book = validate(await readBody(req));
          const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run(book.title, book.author, book.year, book.isbn);
          res.setHeader('Location', `/books/${result.lastInsertRowid}`);
          json(res, 201, byId.get(result.lastInsertRowid)); return;
        }
        res.setHeader('Allow', 'GET, POST');
        throw new HttpError(405, 'Method not allowed');
      }
      const match = /^\/books\/([^/]+)$/.exec(url.pathname);
      if (match) {
        if (!/^[1-9]\d*$/.test(match[1]) || !Number.isSafeInteger(Number(match[1]))) throw new HttpError(400, 'id must be a positive integer');
        const id = Number(match[1]);
        if (!['GET', 'PUT', 'DELETE'].includes(method ?? '')) {
          res.setHeader('Allow', 'GET, PUT, DELETE');
          throw new HttpError(405, 'Method not allowed');
        }
        if (!byId.get(id)) throw new HttpError(404, 'Book not found');
        if (method === 'GET') { json(res, 200, byId.get(id)); return; }
        if (method === 'PUT') {
          const book = validate(await readBody(req));
          const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(book.title, book.author, book.year, book.isbn, id);
          if (!result.changes) throw new HttpError(404, 'Book not found');
          json(res, 200, byId.get(id)); return;
        }
        db.prepare('DELETE FROM books WHERE id = ?').run(id);
        res.writeHead(204); res.end(); return;
      }
      throw new HttpError(404, 'Route not found');
    } catch (error) {
      if (!res.destroyed) json(res, error instanceof HttpError ? error.status : 500, { error: error instanceof HttpError ? error.message : 'Internal server error' });
    }
  });
  server.on('close', () => db.close());
  return server;
}
