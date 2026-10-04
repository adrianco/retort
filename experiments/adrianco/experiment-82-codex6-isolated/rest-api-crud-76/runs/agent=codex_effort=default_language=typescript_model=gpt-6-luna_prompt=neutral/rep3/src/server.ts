import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = { title: string; author: string; year?: number | null; isbn?: string | null };

export function createApp(databasePath = process.env.DATABASE_PATH ?? './books.sqlite'): Server {
  const db = new DatabaseSync(databasePath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const send = (res: ServerResponse, status: number, body: unknown): void => {
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(body));
  };

  const readBody = (req: IncomingMessage): Promise<unknown> => new Promise((resolveBody, reject) => {
    let raw = '';
    req.setEncoding('utf8');
    req.on('data', (chunk: string) => {
      raw += chunk;
      if (raw.length > 1_000_000) reject(new Error('Request body too large'));
    });
    req.on('end', () => {
      try { resolveBody(raw ? JSON.parse(raw) : {}); } catch { reject(new Error('Invalid JSON')); }
    });
    req.on('error', reject);
  });

  const validBook = (value: unknown): value is BookInput => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const book = value as Record<string, unknown>;
    return typeof book.title === 'string' && book.title.trim().length > 0
      && typeof book.author === 'string' && book.author.trim().length > 0
      && (book.year === undefined || book.year === null || (Number.isInteger(book.year) && typeof book.year === 'number'))
      && (book.isbn === undefined || book.isbn === null || typeof book.isbn === 'string');
  };

  const asBook = (row: Record<string, unknown>): Book => ({
    id: Number(row.id), title: String(row.title), author: String(row.author),
    year: row.year === null ? null : Number(row.year), isbn: row.isbn === null ? null : String(row.isbn),
  });

  return createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const route = url.pathname.match(/^\/books(?:\/(\d+))?$/);
    try {
      if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { status: 'ok' });
      if (req.method === 'GET' && url.pathname === '/books') {
        const author = url.searchParams.get('author');
        const rows = author
          ? db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author)
          : db.prepare('SELECT * FROM books ORDER BY id').all();
        return send(res, 200, rows.map((row) => asBook(row as Record<string, unknown>)));
      }
      if (route && req.method === 'POST' && !route[1]) {
        const body = await readBody(req);
        if (!validBook(body)) return send(res, 400, { error: 'title and author are required; year and isbn must be valid' });
        const b = body as BookInput;
        const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
          .run(b.title.trim(), b.author.trim(), b.year ?? null, b.isbn ?? null);
        const row = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(result.lastInsertRowid));
        return send(res, 201, asBook(row as Record<string, unknown>));
      }
      if (route?.[1]) {
        const id = Number(route[1]);
        const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Record<string, unknown> | undefined;
        if (!existing) return send(res, 404, { error: 'Book not found' });
        if (req.method === 'GET') return send(res, 200, asBook(existing));
        if (req.method === 'PUT') {
          const body = await readBody(req);
          if (!validBook(body)) return send(res, 400, { error: 'title and author are required; year and isbn must be valid' });
          const b = body as BookInput;
          db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
            .run(b.title.trim(), b.author.trim(), b.year ?? null, b.isbn ?? null, id);
          const row = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
          return send(res, 200, asBook(row as Record<string, unknown>));
        }
        if (req.method === 'DELETE') {
          db.prepare('DELETE FROM books WHERE id = ?').run(id);
          res.writeHead(204);
          return res.end();
        }
      }
      send(res, 404, { error: 'Not found' });
    } catch (error) {
      send(res, error instanceof Error && error.message === 'Invalid JSON' ? 400 : 500,
        { error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });
}

const currentFile = fileURLToPath(import.meta.url);
if (process.argv[1] && resolve(process.argv[1]) === currentFile) {
  const server = createApp();
  const port = Number(process.env.PORT ?? 3000);
  server.listen(port, () => console.log(`Books API listening on http://localhost:${port}`));
}
