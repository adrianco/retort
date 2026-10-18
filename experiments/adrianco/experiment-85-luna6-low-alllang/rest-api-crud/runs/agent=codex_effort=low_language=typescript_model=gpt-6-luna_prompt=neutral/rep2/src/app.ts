import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Omit<Book, 'id'>;

export function createApp(db: DatabaseSync): Server {
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  return createServer(async (req, res) => {
    try {
      await handleRequest(db, req, res);
    } catch (error) {
      if (error instanceof SyntaxError) return sendJson(res, 400, { error: 'Invalid JSON body' });
      sendJson(res, 500, { error: 'Internal server error' });
    }
  });
}

export async function handleRequest(db: DatabaseSync, req: IncomingMessage, res: ServerResponse): Promise<void> {
  const method = req.method ?? 'GET';
  const url = new URL(req.url ?? '/', 'http://localhost');
  const segments = url.pathname.split('/').filter(Boolean);

  if (method === 'GET' && url.pathname === '/health') return sendJson(res, 200, { status: 'ok' });
  if (segments[0] !== 'books' || segments.length > 2) return sendJson(res, 404, { error: 'Not found' });

  if (segments.length === 1 && method === 'GET') {
    const author = url.searchParams.get('author')?.trim() ?? '';
    const books = author
      ? db.prepare('SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE ORDER BY id').all(`%${author}%`)
      : db.prepare('SELECT * FROM books ORDER BY id').all();
    return sendJson(res, 200, books);
  }

  if (segments.length === 1 && method === 'POST') {
    const input = parseBook(await readJson(req));
    if (!input) return sendJson(res, 400, { error: 'title and author are required; year must be an integer when provided' });
    const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title, input.author, input.year, input.isbn);
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(result.lastInsertRowid));
    return sendJson(res, 201, book);
  }

  if (segments.length === 2) {
    const id = parseId(segments[1]);
    if (id === null) return sendJson(res, 400, { error: 'Invalid book ID' });
    if (method === 'GET') {
      const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
      return book ? sendJson(res, 200, book) : sendJson(res, 404, { error: 'Book not found' });
    }
    if (method === 'PUT') {
      const input = parseBook(await readJson(req));
      if (!input) return sendJson(res, 400, { error: 'title and author are required; year must be an integer when provided' });
      const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
        .run(input.title, input.author, input.year, input.isbn, id);
      if (result.changes === 0) return sendJson(res, 404, { error: 'Book not found' });
      return sendJson(res, 200, db.prepare('SELECT * FROM books WHERE id = ?').get(id));
    }
    if (method === 'DELETE') {
      const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
      if (result.changes === 0) return sendJson(res, 404, { error: 'Book not found' });
      res.writeHead(204).end();
      return;
    }
  }
  sendJson(res, 404, { error: 'Not found' });
}

function parseBook(body: unknown): BookInput | null {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;
  const record = body as Record<string, unknown>;
  if (typeof record.title !== 'string' || !record.title.trim() ||
      typeof record.author !== 'string' || !record.author.trim()) return null;
  if (record.year !== undefined && record.year !== null &&
      (typeof record.year !== 'number' || !Number.isInteger(record.year))) return null;
  if (record.isbn !== undefined && record.isbn !== null && typeof record.isbn !== 'string') return null;
  return {
    title: record.title.trim(),
    author: record.author.trim(),
    year: (record.year as number | null | undefined) ?? null,
    isbn: typeof record.isbn === 'string' ? record.isbn.trim() : null,
  };
}

function parseId(value: string): number | null {
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

function sendJson(res: ServerResponse, status: number, value: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(value));
}

function readJson(req: IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk: string) => { raw += chunk; });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch (error) { reject(error); }
    });
    req.on('error', reject);
  });
}
