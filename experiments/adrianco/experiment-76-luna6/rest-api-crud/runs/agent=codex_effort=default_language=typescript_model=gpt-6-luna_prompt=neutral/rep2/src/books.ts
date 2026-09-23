import { createServer, IncomingMessage, Server, ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Omit<Book, 'id'>;

function json(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(body));
}

async function readBody(request: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of request) {
    raw += chunk;
    if (raw.length > 1_000_000) throw new Error('Request body is too large');
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error('Request body must be valid JSON');
  }
}

function validateBook(value: unknown): BookInput | string {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'Request body must be a JSON object';
  const input = value as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim()) return 'title is required';
  if (typeof input.author !== 'string' || !input.author.trim()) return 'author is required';
  if (input.year !== undefined && input.year !== null && (!Number.isInteger(input.year) || (input.year as number) < 0)) {
    return 'year must be a non-negative integer or null';
  }
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') return 'isbn must be a string or null';
  return {
    title: input.title.trim(),
    author: input.author.trim(),
    year: input.year === undefined ? null : input.year as number | null,
    isbn: input.isbn === undefined ? null : input.isbn as string | null,
  };
}

export function createBookServer(databasePath = process.env.DATABASE_PATH ?? 'books.sqlite'): { server: Server; close: () => void } {
  const db = new DatabaseSync(databasePath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? '/', 'http://localhost');
    const method = request.method ?? 'GET';
    const pathname = url.pathname;

    if (method === 'GET' && pathname === '/health') return json(response, 200, { status: 'ok' });
    if (pathname === '/books' && method === 'GET') {
      const author = url.searchParams.get('author');
      const books = author
        ? db.prepare('SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id').all(author)
        : db.prepare('SELECT * FROM books ORDER BY id').all();
      return json(response, 200, books);
    }
    if (pathname === '/books' && method === 'POST') {
      try {
        const input = validateBook(await readBody(request));
        if (typeof input === 'string') return json(response, 400, { error: input });
        const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
          .run(input.title, input.author, input.year, input.isbn);
        return json(response, 201, { id: Number(result.lastInsertRowid), ...input });
      } catch (error) {
        return json(response, 400, { error: (error as Error).message });
      }
    }

    const match = pathname.match(/^\/books\/([1-9]\d*)$/);
    if (match) {
      const id = Number(match[1]);
      if (!Number.isSafeInteger(id)) return json(response, 400, { error: 'Invalid book ID' });
      if (method === 'GET') {
        const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id);
        return book ? json(response, 200, book) : json(response, 404, { error: 'Book not found' });
      }
      if (method === 'PUT') {
        try {
          const input = validateBook(await readBody(request));
          if (typeof input === 'string') return json(response, 400, { error: input });
          const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
            .run(input.title, input.author, input.year, input.isbn, id);
          if (result.changes === 0) return json(response, 404, { error: 'Book not found' });
          return json(response, 200, { id, ...input });
        } catch (error) {
          return json(response, 400, { error: (error as Error).message });
        }
      }
      if (method === 'DELETE') {
        const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
        return result.changes ? json(response, 200, { message: 'Book deleted' }) : json(response, 404, { error: 'Book not found' });
      }
    }
    return json(response, 404, { error: 'Not found' });
  });

  return { server, close: () => db.close() };
}
