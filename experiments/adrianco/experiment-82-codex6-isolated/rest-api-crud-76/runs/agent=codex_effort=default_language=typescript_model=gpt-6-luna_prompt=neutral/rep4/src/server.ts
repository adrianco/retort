import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { BookStore, type BookInput } from './books.js';

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function readBody(req: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  if (!raw) return {};
  try { return JSON.parse(raw); } catch { throw new Error('Request body must be valid JSON'); }
}

function validInput(body: unknown): body is BookInput {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return false;
  const value = body as Record<string, unknown>;
  return typeof value.title === 'string' && value.title.trim().length > 0
    && typeof value.author === 'string' && value.author.trim().length > 0
    && (value.year === undefined || value.year === null || (Number.isInteger(value.year) && typeof value.year === 'number'))
    && (value.isbn === undefined || value.isbn === null || typeof value.isbn === 'string');
}

export function createApp(store = new BookStore()) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const path = url.pathname;
    if (req.method === 'GET' && path === '/health') return send(res, 200, { status: 'ok' });
    if (path === '/books' && req.method === 'GET') return send(res, 200, store.list(url.searchParams.get('author') ?? undefined));
    if (path === '/books' && req.method === 'POST') {
      try {
        const body = await readBody(req);
        if (!validInput(body)) return send(res, 400, { error: 'title and author are required; year must be an integer and isbn a string' });
        return send(res, 201, store.create(body));
      } catch (error) { return send(res, 400, { error: (error as Error).message }); }
    }
    const match = path.match(/^\/books\/(\d+)$/);
    if (match) {
      const id = Number(match[1]);
      if (!Number.isSafeInteger(id)) return send(res, 400, { error: 'Invalid book ID' });
      if (req.method === 'GET') {
        const book = store.get(id);
        return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
      }
      if (req.method === 'PUT') {
        try {
          const body = await readBody(req);
          if (!validInput(body)) return send(res, 400, { error: 'title and author are required; year must be an integer and isbn a string' });
          const book = store.update(id, body);
          return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
        } catch (error) { return send(res, 400, { error: (error as Error).message }); }
      }
      if (req.method === 'DELETE') return store.delete(id) ? send(res, 200, { message: 'Book deleted' }) : send(res, 404, { error: 'Book not found' });
    }
    return send(res, 404, { error: 'Not found' });
  });
  return { server, store };
}

if (process.argv[1]?.endsWith('/server.js') || process.argv[1]?.endsWith('/server.ts')) {
  const { server } = createApp();
  const port = Number(process.env.PORT ?? 3000);
  server.listen(port, () => console.log(`Book API listening on http://localhost:${port}`));
}
