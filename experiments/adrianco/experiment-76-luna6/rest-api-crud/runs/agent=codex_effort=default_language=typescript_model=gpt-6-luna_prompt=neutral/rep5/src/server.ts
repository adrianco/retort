import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { BookStore, validateBook } from './books.js';

function send(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  let text = '';
  for await (const chunk of req) {
    text += chunk.toString();
    if (text.length > 1_000_000) throw new Error('Request body is too large');
  }
  try { return JSON.parse(text); } catch { throw new Error('Request body must contain valid JSON'); }
}

export function createApp(store = new BookStore()): Server {
  return createServer(async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const method = req.method ?? 'GET';
    if (url.pathname === '/health' && method === 'GET') return send(res, 200, { status: 'ok' });
    if (url.pathname === '/books' && method === 'GET') return send(res, 200, store.list(url.searchParams.get('author') ?? undefined));
    if (url.pathname === '/books' && method === 'POST') {
      try {
        const validated = validateBook(await readJson(req));
        if (validated.error) return send(res, 400, { error: validated.error });
        return send(res, 201, store.create(validated.input!));
      } catch (error) { return send(res, 400, { error: (error as Error).message }); }
    }
    const match = url.pathname.match(/^\/books\/([^/]+)$/);
    if (match) {
      const id = Number(match[1]);
      if (!Number.isSafeInteger(id) || id < 1) return send(res, 400, { error: 'id must be a positive integer' });
      if (method === 'GET') {
        const book = store.get(id);
        return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
      }
      if (method === 'PUT') {
        try {
          const validated = validateBook(await readJson(req));
          if (validated.error) return send(res, 400, { error: validated.error });
          const book = store.update(id, validated.input!);
          return book ? send(res, 200, book) : send(res, 404, { error: 'Book not found' });
        } catch (error) { return send(res, 400, { error: (error as Error).message }); }
      }
      if (method === 'DELETE') return store.delete(id) ? send(res, 200, { deleted: true }) : send(res, 404, { error: 'Book not found' });
    }
    send(res, 404, { error: 'Route not found' });
  });
}

if (require.main === module) {
  const server = createApp();
  const port = Number(process.env.PORT ?? 3000);
  server.listen(port, () => console.log(`Book API listening on port ${port}`));
  const shutdown = () => server.close(() => process.exit(0));
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}
