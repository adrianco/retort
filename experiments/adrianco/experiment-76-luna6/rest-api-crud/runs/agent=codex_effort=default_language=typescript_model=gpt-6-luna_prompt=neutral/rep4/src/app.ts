import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

interface BookInput { title: string; author: string; year: number | null; isbn: string | null }
interface BookRow extends BookInput { id: number }

function json(res: ServerResponse, status: number, body?: unknown): void {
  res.statusCode = status;
  if (body === undefined) return res.end();
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(body));
}

async function readBody(req: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  if (!raw) return {};
  return JSON.parse(raw);
}

function parseInput(body: unknown): { value?: BookInput; error?: string } {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return { error: 'Request body must be a JSON object' };
  const input = body as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim()) return { error: 'Title is required' };
  if (typeof input.author !== 'string' || !input.author.trim()) return { error: 'Author is required' };
  if (input.year !== undefined && input.year !== null && (!Number.isInteger(input.year) || (input.year as number) < 0)) return { error: 'Year must be a non-negative integer' };
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') return { error: 'ISBN must be a string' };
  return { value: {
    title: input.title.trim(), author: input.author.trim(),
    year: (input.year as number | null | undefined) ?? null,
    isbn: typeof input.isbn === 'string' ? input.isbn.trim() || null : null,
  } };
}

export function createApp(db: DatabaseSync = new DatabaseSync(process.env.DATABASE_PATH ?? 'books.sqlite')) {
  return createServer(createHandler(db));
}

export function createHandler(db: DatabaseSync) {
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);
  return async (req: IncomingMessage, res: ServerResponse) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const path = url.pathname.replace(/\/$/, '') || '/';
      if (req.method === 'GET' && path === '/health') return json(res, 200, { status: 'ok' });
      if (path === '/books' && req.method === 'GET') {
        const author = url.searchParams.get('author')?.trim();
        const books = author
          ? db.prepare('SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id').all(author)
          : db.prepare('SELECT * FROM books ORDER BY id').all();
        return json(res, 200, books);
      }
      if (path === '/books' && req.method === 'POST') {
        let body: unknown;
        try { body = await readBody(req); } catch { return json(res, 400, { error: 'Invalid JSON body' }); }
        const parsed = parseInput(body);
        if (!parsed.value) return json(res, 400, { error: parsed.error });
        const { title, author, year, isbn } = parsed.value;
        const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run(title, author, year, isbn);
        return json(res, 201, db.prepare('SELECT * FROM books WHERE id = ?').get(Number(result.lastInsertRowid)) as BookRow);
      }
      const match = path.match(/^\/books\/([^/]+)$/);
      if (match) {
        const id = Number(match[1]);
        if (!Number.isSafeInteger(id) || id < 1) return json(res, 400, { error: 'Invalid book ID' });
        if (req.method === 'GET') {
          const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
          return book ? json(res, 200, book) : json(res, 404, { error: 'Book not found' });
        }
        if (req.method === 'PUT') {
          if (!db.prepare('SELECT id FROM books WHERE id = ?').get(id)) return json(res, 404, { error: 'Book not found' });
          let body: unknown;
          try { body = await readBody(req); } catch { return json(res, 400, { error: 'Invalid JSON body' }); }
          const parsed = parseInput(body);
          if (!parsed.value) return json(res, 400, { error: parsed.error });
          const { title, author, year, isbn } = parsed.value;
          db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(title, author, year, isbn, id);
          return json(res, 200, db.prepare('SELECT * FROM books WHERE id = ?').get(id));
        }
        if (req.method === 'DELETE') {
          const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
          return result.changes ? json(res, 204) : json(res, 404, { error: 'Book not found' });
        }
      }
      return json(res, 404, { error: 'Route not found' });
    } catch {
      return json(res, 500, { error: 'Internal server error' });
    }
  };
}
