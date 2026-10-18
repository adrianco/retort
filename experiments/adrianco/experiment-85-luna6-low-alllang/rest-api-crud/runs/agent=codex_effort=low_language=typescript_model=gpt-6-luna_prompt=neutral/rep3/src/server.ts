import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { BookStore, type BookInput } from './books.js';

const store = new BookStore();

function send(res: ServerResponse, status: number, data: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

async function body(req: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of req) {
    raw += chunk;
    if (raw.length > 1_000_000) throw new Error('Request body too large');
  }
  try { return JSON.parse(raw); } catch { throw new SyntaxError('Request body must be valid JSON'); }
}

function validate(value: unknown): BookInput | string {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return 'Request body must be a JSON object';
  const input = value as Record<string, unknown>;
  if (typeof input.title !== 'string' || !input.title.trim()) return 'title is required';
  if (typeof input.author !== 'string' || !input.author.trim()) return 'author is required';
  if (input.year !== undefined && input.year !== null && (!Number.isInteger(input.year) || typeof input.year !== 'number')) return 'year must be an integer or null';
  if (input.isbn !== undefined && input.isbn !== null && typeof input.isbn !== 'string') return 'isbn must be a string or null';
  return { title: input.title.trim(), author: input.author.trim(), year: input.year as number | null | undefined, isbn: input.isbn as string | null | undefined };
}

export function createApp(bookStore = store) {
  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);
      if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { status: 'ok' });
      if (url.pathname === '/books' && req.method === 'GET') return send(res, 200, bookStore.list(url.searchParams.get('author') ?? undefined));
      if (url.pathname === '/books' && req.method === 'POST') {
        let parsed: unknown;
        try { parsed = await body(req); } catch (error) { return send(res, 400, { error: (error as Error).message }); }
        const input = validate(parsed);
        if (typeof input === 'string') return send(res, 400, { error: input });
        return send(res, 201, bookStore.create(input));
      }
      const match = url.pathname.match(/^\/books\/(\d+)$/);
      if (match) {
        const id = Number(match[1]);
        if (req.method === 'GET') {
          const book = bookStore.get(id);
          return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
        }
        if (req.method === 'PUT') {
          let parsed: unknown;
          try { parsed = await body(req); } catch (error) { return send(res, 400, { error: (error as Error).message }); }
          const input = validate(parsed);
          if (typeof input === 'string') return send(res, 400, { error: input });
          const book = bookStore.update(id, input);
          return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
        }
        if (req.method === 'DELETE') return bookStore.delete(id) ? send(res, 200, { message: 'Book deleted' }) : send(res, 404, { error: 'Book not found' });
      }
      return send(res, 404, { error: 'Route not found' });
    } catch (error) {
      return send(res, (error as Error).message === 'Request body too large' ? 413 : 500, { error: 'Internal server error' });
    }
  });
}

if (process.argv[1]?.endsWith('/server.js') || process.argv[1]?.endsWith('/server.ts')) {
  const port = Number(process.env.PORT ?? 3000);
  createApp().listen(port, () => console.log(`Book API listening on http://localhost:${port}`));
}
