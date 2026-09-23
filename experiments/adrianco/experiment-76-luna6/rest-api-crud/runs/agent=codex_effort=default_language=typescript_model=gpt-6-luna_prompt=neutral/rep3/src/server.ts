import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { resolve } from 'node:path';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Omit<Book, 'id'>;
type BookPayload = { title?: unknown; author?: unknown; year?: unknown; isbn?: unknown };

const MAX_BODY_BYTES = 1024 * 1024;

function sendJson(response: ServerResponse, status: number, body: unknown): void {
  response.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(body));
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  let body = '';
  for await (const chunk of request) {
    body += chunk.toString();
    if (Buffer.byteLength(body) > MAX_BODY_BYTES) throw Object.assign(new Error('Request body too large'), { status: 413 });
  }
  try { return JSON.parse(body); }
  catch { throw Object.assign(new Error('Request body must be valid JSON'), { status: 400 }); }
}

export function validateBook(payload: unknown): { value?: BookInput; error?: string } {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return { error: 'Body must be a JSON object' };
  const book = payload as BookPayload;
  if (typeof book.title !== 'string' || !book.title.trim()) return { error: 'title is required' };
  if (typeof book.author !== 'string' || !book.author.trim()) return { error: 'author is required' };
  if (book.year !== undefined && book.year !== null && (!Number.isInteger(book.year) || (book.year as number) < 0)) {
    return { error: 'year must be a non-negative integer or null' };
  }
  if (book.isbn !== undefined && book.isbn !== null && typeof book.isbn !== 'string') return { error: 'isbn must be a string or null' };
  return { value: {
    title: book.title.trim(), author: book.author.trim(),
    year: (book.year as number | null | undefined) ?? null,
    isbn: typeof book.isbn === 'string' ? book.isbn.trim() : null,
  } };
}

export function createBookStore(databasePath: string): {
  create(book: BookInput): Book;
  list(author?: string | null): Book[];
  get(id: number): Book | undefined;
  update(id: number, book: BookInput): Book | undefined;
  delete(id: number): boolean;
  close(): void;
} {
  const db = new DatabaseSync(resolve(databasePath));
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const findBook = db.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?');
  const listBooks = db.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id');
  const listByAuthor = db.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id');
  return {
    create(book) {
      const result = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
        .run(book.title, book.author, book.year, book.isbn);
      return findBook.get(Number(result.lastInsertRowid)) as unknown as Book;
    },
    list(author = null) {
      return (author === null ? listBooks.all() : listByAuthor.all(author)) as unknown as Book[];
    },
    get(id) { return findBook.get(id) as unknown as Book | undefined; },
    update(id, book) {
      const result = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
        .run(book.title, book.author, book.year, book.isbn, id);
      return Number(result.changes) === 0 ? undefined : findBook.get(id) as unknown as Book;
    },
    delete(id) { return Number(db.prepare('DELETE FROM books WHERE id = ?').run(id).changes) > 0; },
    close() { db.close(); },
  };
}

export function createApp(databasePath = process.env.DATABASE_PATH ?? './books.sqlite'): Server {
  const store = createBookStore(databasePath);
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? '/', 'http://localhost');
      const path = url.pathname.replace(/\/$/, '') || '/';
      const method = request.method ?? 'GET';

      if (method === 'GET' && path === '/health') return sendJson(response, 200, { status: 'ok' });
      if (path === '/books' && method === 'GET') {
        const author = url.searchParams.get('author');
        const books = store.list(author);
        return sendJson(response, 200, books);
      }
      if (path === '/books' && method === 'POST') {
        const result = validateBook(await readJson(request));
        if (!result.value) return sendJson(response, 400, { error: result.error });
        return sendJson(response, 201, store.create(result.value));
      }

      const match = path.match(/^\/books\/(\d+)$/);
      if (match) {
        const id = Number(match[1]);
        if (!Number.isSafeInteger(id) || id <= 0) return sendJson(response, 400, { error: 'Invalid book id' });
        if (method === 'GET') {
          const book = store.get(id);
          return book ? sendJson(response, 200, book) : sendJson(response, 404, { error: 'Book not found' });
        }
        if (method === 'PUT') {
          const result = validateBook(await readJson(request));
          if (!result.value) return sendJson(response, 400, { error: result.error });
          const book = store.update(id, result.value);
          return !book
            ? sendJson(response, 404, { error: 'Book not found' })
            : sendJson(response, 200, book);
        }
        if (method === 'DELETE') {
          return !store.delete(id) ? sendJson(response, 404, { error: 'Book not found' }) : sendJson(response, 204, undefined);
        }
      }
      sendJson(response, 404, { error: 'Not found' });
    } catch (error) {
      const err = error as Error & { status?: number };
      sendJson(response, err.status ?? 500, { error: err.status ? err.message : 'Internal server error' });
    }
  });
  server.on('close', () => store.close());
  return server;
}

if (process.argv[1] && import.meta.url === new URL(`file://${resolve(process.argv[1])}`).href) {
  const port = Number(process.env.PORT ?? 3000);
  createApp().listen(port, () => console.log(`Book API listening on http://localhost:${port}`));
}
