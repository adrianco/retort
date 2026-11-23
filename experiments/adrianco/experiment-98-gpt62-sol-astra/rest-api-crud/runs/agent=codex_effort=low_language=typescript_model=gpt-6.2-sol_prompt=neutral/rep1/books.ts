import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';

type BookInput = {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

class RequestError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

function json(response: ServerResponse, status: number, body: unknown) {
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(body));
}

async function readBook(request: IncomingMessage): Promise<BookInput> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request.iterator({ destroyOnReturn: false })) {
    size += chunk.length;
    if (size > 64 * 1024) {
      request.resume();
      throw new RequestError(413, 'Request body exceeds 64 KiB');
    }
    chunks.push(chunk);
  }

  let body: unknown;
  try {
    body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } catch {
    throw new RequestError(400, 'Request body must be valid JSON');
  }
  if (body === null || typeof body !== 'object' || Array.isArray(body)) {
    throw new RequestError(400, 'Request body must be a JSON object');
  }

  const { title, author, year = null, isbn = null } = body as Record<string, unknown>;
  if (typeof title !== 'string' || !title.trim() || typeof author !== 'string' || !author.trim()) {
    throw new RequestError(400, 'Title and author must be non-empty strings');
  }
  if (year !== null && (typeof year !== 'number' || !Number.isSafeInteger(year))) {
    throw new RequestError(400, 'Year must be an integer or null');
  }
  if (isbn !== null && (typeof isbn !== 'string' || !isbn.trim())) {
    throw new RequestError(400, 'ISBN must be a non-empty string or null');
  }

  return { title: title.trim(), author: author.trim(), year, isbn: isbn?.trim() ?? null };
}

export function createBookServer(databasePath: string) {
  const db = new DatabaseSync(databasePath);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  const list = db.prepare('SELECT * FROM books ORDER BY id');
  const listByAuthor = db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id');
  const find = db.prepare('SELECT * FROM books WHERE id = ?');
  const insert = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *');
  const update = db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING *');
  const remove = db.prepare('DELETE FROM books WHERE id = ?');

  async function handle(request: IncomingMessage, response: ServerResponse) {
    const { pathname, searchParams } = new URL(request.url ?? '/', 'http://localhost');
    const method = request.method;

    if (pathname === '/health') {
      if (method === 'GET') return json(response, 200, { status: 'ok' });
      response.setHeader('Allow', 'GET');
      throw new RequestError(405, 'Method not allowed');
    }

    if (pathname === '/books') {
      if (method === 'GET') {
        const author = searchParams.get('author');
        return json(response, 200, author === null ? list.all() : listByAuthor.all(author));
      }
      if (method === 'POST') {
        const { title, author, year, isbn } = await readBook(request);
        const book = insert.get(title, author, year, isbn)!;
        response.setHeader('Location', `/books/${book.id}`);
        return json(response, 201, book);
      }
      response.setHeader('Allow', 'GET, POST');
      throw new RequestError(405, 'Method not allowed');
    }

    const match = /^\/books\/([^/]+)$/.exec(pathname);
    if (!match) throw new RequestError(404, 'Route not found');
    const id = Number(match[1]);
    if (!/^\d+$/.test(match[1]) || !Number.isSafeInteger(id) || id < 1) {
      throw new RequestError(400, 'Book ID must be a positive integer');
    }

    switch (method) {
      case 'GET': {
        const book = find.get(id);
        if (!book) throw new RequestError(404, 'Book not found');
        return json(response, 200, book);
      }
      case 'PUT': {
        const { title, author, year, isbn } = await readBook(request);
        const book = update.get(title, author, year, isbn, id);
        if (!book) throw new RequestError(404, 'Book not found');
        return json(response, 200, book);
      }
      case 'DELETE':
        if (!remove.run(id).changes) throw new RequestError(404, 'Book not found');
        response.writeHead(204).end();
        return;
      default:
        response.setHeader('Allow', 'GET, PUT, DELETE');
        throw new RequestError(405, 'Method not allowed');
    }
  }

  const server = createServer((request, response) => {
    void handle(request, response).catch((error: unknown) => {
      if (response.destroyed) return;
      if (error instanceof RequestError) {
        json(response, error.status, { error: error.message });
      } else {
        console.error(error);
        json(response, 500, { error: 'Internal server error' });
      }
    });
  });
  server.once('close', () => db.close());
  return server;
}
