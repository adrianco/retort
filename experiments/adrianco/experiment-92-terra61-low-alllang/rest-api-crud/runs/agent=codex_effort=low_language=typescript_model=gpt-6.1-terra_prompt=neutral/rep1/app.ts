import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

interface BookInput { title: string; author: string; year: number | null; isbn: string | null }

function validate(value: unknown): BookInput | string {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'Body must be a JSON object';
  const book = value as Record<string, unknown>;
  if (typeof book.title !== 'string' || !book.title.trim()) return 'title is required';
  if (typeof book.author !== 'string' || !book.author.trim()) return 'author is required';
  if (book.year != null && (!Number.isSafeInteger(book.year) || (book.year as number) < 0)) return 'year must be a non-negative integer or null';
  if (book.isbn != null && typeof book.isbn !== 'string') return 'isbn must be a string or null';
  return { title: book.title.trim(), author: book.author.trim(), year: (book.year as number | null | undefined) ?? null, isbn: (book.isbn as string | null | undefined) ?? null };
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buffer = Buffer.from(chunk);
    size += buffer.length;
    if (size > 1024 * 1024) throw new Error('Body too large');
    chunks.push(buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

export function createApp(databasePath = 'books.sqlite') {
  const db = new DatabaseSync(databasePath);
  db.exec('CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)');
  const get = db.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?');
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const method = req.method;
      if (url.pathname === '/health' && method === 'GET') return send(res, 200, { status: 'ok' });
      if (url.pathname === '/books' && method === 'GET') {
        const author = url.searchParams.get('author');
        const books = author === null
          ? db.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id').all()
          : db.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id').all(author);
        return send(res, 200, books);
      }
      const match = /^\/books\/([1-9]\d*)$/.exec(url.pathname);
      if (match && !Number.isSafeInteger(Number(match[1]))) return send(res, 404, { error: 'Book not found' });
      const id = match ? Number(match[1]) : undefined;
      if (id !== undefined && method === 'GET') {
        const book = get.get(id);
        return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
      }
      if (id !== undefined && method === 'DELETE') {
        const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
        return result.changes ? send(res, 200, { message: 'Book deleted' }) : send(res, 404, { error: 'Book not found' });
      }
      if ((url.pathname === '/books' && method === 'POST') || (id !== undefined && method === 'PUT')) {
        if (id !== undefined && !get.get(id)) return send(res, 404, { error: 'Book not found' });
        let body: unknown;
        try { body = await readJson(req); } catch (error) {
          return send(res, error instanceof Error && error.message === 'Body too large' ? 413 : 400, { error: error instanceof Error && error.message === 'Body too large' ? 'Body too large' : 'Invalid JSON' });
        }
        const book = validate(body);
        if (typeof book === 'string') return send(res, 400, { error: book });
        if (id === undefined) {
          const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run(book.title, book.author, book.year, book.isbn);
          return send(res, 201, get.get(result.lastInsertRowid));
        }
        db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(book.title, book.author, book.year, book.isbn, id);
        return send(res, 200, get.get(id));
      }
      return send(res, 404, { error: 'Not found' });
    } catch (error) {
      console.error(error);
      if (!res.headersSent) send(res, 500, { error: 'Internal server error' });
      else res.end();
    }
  });
  server.on('close', () => db.close());
  return server;
}
