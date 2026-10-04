import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { BookStore, type BookInput } from './books.js';

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  try { return JSON.parse(raw); } catch { throw new Error('Request body must be valid JSON'); }
}

function validate(value: unknown): BookInput | string {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'Request body must be a JSON object';
  const data = value as Record<string, unknown>;
  if (typeof data.title !== 'string' || !data.title.trim()) return 'title is required';
  if (typeof data.author !== 'string' || !data.author.trim()) return 'author is required';
  if (data.year !== undefined && data.year !== null && (!Number.isInteger(data.year) || typeof data.year !== 'number')) return 'year must be an integer or null';
  if (data.isbn !== undefined && data.isbn !== null && typeof data.isbn !== 'string') return 'isbn must be a string or null';
  return { title: data.title, author: data.author, year: data.year as number | null | undefined, isbn: data.isbn as string | null | undefined };
}

export function createApp(db = new DatabaseSync('books.db')): Server {
  const store = new BookStore(db);
  return createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const path = url.pathname;
    if (req.method === 'GET' && path === '/health') return send(res, 200, { status: 'ok' });
    if (path === '/books' && req.method === 'GET') return send(res, 200, store.list(url.searchParams.get('author') ?? undefined));
    if (path === '/books' && req.method === 'POST') {
      try {
        const input = validate(await readJson(req));
        if (typeof input === 'string') return send(res, 400, { error: input });
        return send(res, 201, store.create(input));
      } catch (error) { return send(res, 400, { error: error instanceof Error ? error.message : 'Invalid request' }); }
    }
    const match = path.match(/^\/books\/([^/]+)$/);
    if (match) {
      const id = decodeURIComponent(match[1]!);
      if (req.method === 'GET') {
        const book = store.get(id);
        return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
      }
      if (req.method === 'PUT') {
        try {
          const input = validate(await readJson(req));
          if (typeof input === 'string') return send(res, 400, { error: input });
          const book = store.update(id, input);
          return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
        } catch (error) { return send(res, 400, { error: error instanceof Error ? error.message : 'Invalid request' }); }
      }
      if (req.method === 'DELETE') return store.delete(id) ? (res.writeHead(204).end(), undefined) : send(res, 404, { error: 'Book not found' });
    }
    return send(res, 404, { error: 'Not found' });
  });
}
