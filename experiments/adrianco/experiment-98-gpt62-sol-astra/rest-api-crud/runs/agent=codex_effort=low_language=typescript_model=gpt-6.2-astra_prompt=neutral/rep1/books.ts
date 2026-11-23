import { DatabaseSync } from 'node:sqlite';

class InvalidBook extends Error {}

function bookFields(value: unknown): [string, string, number | null, string | null] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new InvalidBook('Expected a JSON object');
  }
  const { title, author, year = null, isbn = null } = value as Record<string, unknown>;
  if (typeof title !== 'string' || !title.trim()) throw new InvalidBook('title is required');
  if (typeof author !== 'string' || !author.trim()) throw new InvalidBook('author is required');
  if (year !== null && (typeof year !== 'number' || !Number.isSafeInteger(year))) {
    throw new InvalidBook('year must be an integer');
  }
  if (isbn !== null && typeof isbn !== 'string') throw new InvalidBook('isbn must be a string');
  return [title.trim(), author.trim(), year, isbn];
}

const error = (status: number, message: string, headers?: HeadersInit) =>
  Response.json({ error: message }, { status, headers });

export function openCollection(path: string) {
  const db = new DatabaseSync(path);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT
  ) STRICT`);

  async function handle(request: Request): Promise<Response> {
    const { pathname, searchParams } = new URL(request.url);
    const method = request.method;
    const collection = pathname === '/books';
    const item = /^\/books\/([1-9]\d*)$/.exec(pathname);
    const health = pathname === '/health';
    if (!health && !collection && !item) return error(404, 'Route not found');
    const allowed = health ? ['GET'] : collection ? ['GET', 'POST'] : ['GET', 'PUT', 'DELETE'];
    if (!allowed.includes(method)) return error(405, 'Method not allowed', { Allow: allowed.join(', ') });

    if (health) {
      db.prepare('SELECT 1').get();
      return Response.json({ status: 'ok' });
    }

    const id = item?.[1] ?? '';
    if (collection && method === 'GET') {
      const author = searchParams.get('author');
      const books = author === null
        ? db.prepare('SELECT * FROM books ORDER BY id').all()
        : db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author);
      return Response.json(books);
    }

    if (method === 'POST' || method === 'PUT') {
      let fields: ReturnType<typeof bookFields>;
      try {
        fields = bookFields(await request.json());
      } catch (err) {
        if (err instanceof SyntaxError) return error(400, 'Invalid JSON');
        if (err instanceof InvalidBook) return error(400, err.message);
        throw err;
      }
      if (method === 'POST') {
        const book = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *').get(...fields)!;
        return Response.json(book, { status: 201, headers: { Location: '/books/' + book.id } });
      }
      const book = db.prepare('UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=? RETURNING *').get(...fields, id);
      return book ? Response.json(book) : error(404, 'Book not found');
    }

    if (method === 'DELETE') {
      const result = db.prepare('DELETE FROM books WHERE id=?').run(id);
      return result.changes ? new Response(null, { status: 204 }) : error(404, 'Book not found');
    }
    const book = db.prepare('SELECT * FROM books WHERE id=?').get(id);
    return book ? Response.json(book) : error(404, 'Book not found');
  }

  return { handle, close: () => db.close() };
}
