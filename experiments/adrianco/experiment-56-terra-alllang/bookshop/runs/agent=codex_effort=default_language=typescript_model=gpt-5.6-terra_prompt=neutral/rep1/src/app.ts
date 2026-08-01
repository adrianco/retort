import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}

export interface AppOptions {
  databasePath?: string;
}

function sendJson(response: ServerResponse, status: number, value: unknown): void {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(value));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function validateOptionalFields(input: BookInput): string | undefined {
  if (input.year !== undefined && (!Number.isInteger(input.year) || typeof input.year !== 'number')) {
    return 'year must be an integer';
  }
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') {
    return 'isbn must be a string or null';
  }
  return undefined;
}

async function readJson(request: IncomingMessage): Promise<BookInput> {
  let body = '';
  for await (const chunk of request) body += chunk;
  if (!body) return {};
  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error();
    return parsed as BookInput;
  } catch {
    throw new Error('Request body must be valid JSON object');
  }
}

function parseId(segment: string): number | undefined {
  const id = Number(segment);
  return Number.isSafeInteger(id) && id > 0 ? id : undefined;
}

/** Creates an HTTP server backed by a SQLite database. Call close() to release it. */
export function createApp(options: AppOptions = {}): Server {
  const database = new DatabaseSync(options.databasePath ?? 'books.db');
  database.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);

  const server = createServer(async (request, response) => {
    const method = request.method ?? 'GET';
    const url = new URL(request.url ?? '/', 'http://localhost');
    const match = url.pathname.match(/^\/books\/(\d+)$/);

    try {
      if (method === 'GET' && url.pathname === '/health') {
        return sendJson(response, 200, { status: 'ok' });
      }

      if (method === 'GET' && url.pathname === '/books') {
        const author = url.searchParams.get('author');
        const books = author === null
          ? database.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id').all()
          : database.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id').all(author);
        return sendJson(response, 200, books);
      }

      if (match) {
        const id = parseId(match[1]);
        if (id === undefined) return sendJson(response, 400, { error: 'Invalid book id' });
        const current = database.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?').get(id) as Book | undefined;

        if (method === 'GET') {
          return current ? sendJson(response, 200, current) : sendJson(response, 404, { error: 'Book not found' });
        }
        if (method === 'DELETE') {
          if (!current) return sendJson(response, 404, { error: 'Book not found' });
          database.prepare('DELETE FROM books WHERE id = ?').run(id);
          response.writeHead(204);
          return response.end();
        }
        if (method === 'PUT') {
          if (!current) return sendJson(response, 404, { error: 'Book not found' });
          const input = await readJson(request);
          const fieldError = validateOptionalFields(input);
          if (fieldError) return sendJson(response, 400, { error: fieldError });
          if (input.title !== undefined && !isNonEmptyString(input.title)) return sendJson(response, 400, { error: 'title is required' });
          if (input.author !== undefined && !isNonEmptyString(input.author)) return sendJson(response, 400, { error: 'author is required' });
          if (Object.keys(input).length === 0) return sendJson(response, 400, { error: 'Provide at least one field to update' });

          const updated = {
            title: input.title === undefined ? current.title : input.title.trim(),
            author: input.author === undefined ? current.author : input.author.trim(),
            year: input.year === undefined ? current.year : input.year,
            isbn: input.isbn === undefined ? current.isbn : input.isbn
          };
          database.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
            .run(updated.title, updated.author, updated.year, updated.isbn, id);
          return sendJson(response, 200, { id, ...updated });
        }
      }

      if (method === 'POST' && url.pathname === '/books') {
        const input = await readJson(request);
        if (!isNonEmptyString(input.title)) return sendJson(response, 400, { error: 'title is required' });
        if (!isNonEmptyString(input.author)) return sendJson(response, 400, { error: 'author is required' });
        const fieldError = validateOptionalFields(input);
        if (fieldError) return sendJson(response, 400, { error: fieldError });
        const result = database.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
          .run(input.title.trim(), input.author.trim(), input.year ?? null, input.isbn ?? null);
        const book: Book = { id: Number(result.lastInsertRowid), title: input.title.trim(), author: input.author.trim(), year: input.year as number ?? null, isbn: input.isbn as string ?? null };
        return sendJson(response, 201, book);
      }

      return sendJson(response, 404, { error: 'Route not found' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unexpected error';
      return sendJson(response, 400, { error: message });
    }
  });

  server.on('close', () => database.close());
  return server;
}
