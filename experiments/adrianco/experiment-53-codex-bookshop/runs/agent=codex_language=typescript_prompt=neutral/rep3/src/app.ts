import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { BookRepository, type BookInput } from './database.ts';

export function parseBook(body: unknown): { value?: BookInput; error?: string } {
  if (!body || typeof body !== 'object') return { error: 'Request body must be a JSON object' };
  const candidate = body as Record<string, unknown>;
  if (typeof candidate.title !== 'string' || !candidate.title.trim()) return { error: 'title is required' };
  if (typeof candidate.author !== 'string' || !candidate.author.trim()) return { error: 'author is required' };
  if (candidate.year !== undefined && candidate.year !== null && (!Number.isInteger(candidate.year) || (candidate.year as number) < 0)) return { error: 'year must be a non-negative integer' };
  if (candidate.isbn !== undefined && candidate.isbn !== null && typeof candidate.isbn !== 'string') return { error: 'isbn must be a string' };
  return { value: { title: candidate.title.trim(), author: candidate.author.trim(), year: candidate.year as number | null | undefined, isbn: candidate.isbn as string | null | undefined } };
}

function idOf(value: string): number | null {
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  let raw = '';
  for await (const chunk of request) raw += chunk;
  try { return JSON.parse(raw); } catch { throw new Error('Invalid JSON'); }
}

function send(response: ServerResponse, status: number, payload?: unknown): void {
  response.statusCode = status;
  if (payload === undefined) return response.end();
  response.setHeader('content-type', 'application/json; charset=utf-8');
  response.end(JSON.stringify(payload));
}

export function createApp(databasePath = ':memory:') {
  const repository = new BookRepository(new DatabaseSync(databasePath));
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? '/', `http://${request.headers.host ?? 'localhost'}`);
      const parts = url.pathname.split('/').filter(Boolean);
      const method = request.method ?? 'GET';
      if (method === 'GET' && url.pathname === '/health') return send(response, 200, { status: 'ok' });
      if (method === 'GET' && url.pathname === '/books') return send(response, 200, repository.list(url.searchParams.get('author') ?? undefined));
      if (method === 'POST' && url.pathname === '/books') {
        const parsed = parseBook(await readJson(request));
        if (parsed.error) return send(response, 400, { error: parsed.error });
        return send(response, 201, repository.create(parsed.value!));
      }
      if (parts[0] !== 'books' || parts.length !== 2 || idOf(parts[1]) === null) return send(response, 404, { error: 'Route not found' });
      const id = idOf(parts[1])!;
      if (method === 'GET') {
        const book = repository.find(id);
        return book ? send(response, 200, book) : send(response, 404, { error: 'Book not found' });
      }
      if (method === 'PUT') {
        const parsed = parseBook(await readJson(request));
        if (parsed.error) return send(response, 400, { error: parsed.error });
        const book = repository.update(id, parsed.value!);
        return book ? send(response, 200, book) : send(response, 404, { error: 'Book not found' });
      }
      if (method === 'DELETE') return repository.delete(id) ? send(response, 204) : send(response, 404, { error: 'Book not found' });
      return send(response, 405, { error: 'Method not allowed' });
    } catch (error) {
      return send(response, error instanceof Error && error.message === 'Invalid JSON' ? 400 : 500, { error: error instanceof Error && error.message === 'Invalid JSON' ? error.message : 'Internal server error' });
    }
  });
  return { server, close: () => repository.close() };
}
