import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { BookRepository, type Database } from './db.js';
import { parseId, validateBook } from './validation.js';

const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly details?: Record<string, string>,
  ) {
    super(message);
  }
}

function send(res: ServerResponse, status: number, payload?: unknown): void {
  if (payload === undefined) {
    res.writeHead(status);
    res.end();
    return;
  }
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

function sendError(res: ServerResponse, status: number, message: string, details?: Record<string, string>): void {
  send(res, status, details ? { error: message, details } : { error: message });
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new HttpError(413, 'request body too large');
    chunks.push(chunk as Buffer);
  }
  const text = Buffer.concat(chunks).toString('utf8');
  if (text.trim().length === 0) throw new HttpError(400, 'request body is required');
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, 'request body is not valid JSON');
  }
}

function requireId(raw: string): number {
  const id = parseId(raw);
  if (id === null) throw new HttpError(400, 'book id must be a positive integer');
  return id;
}

export function createApp(db: Database): Server {
  const books = new BookRepository(db);

  const handle = async (req: IncomingMessage, res: ServerResponse): Promise<void> => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const method = req.method ?? 'GET';
    const path = url.pathname.replace(/\/+$/, '') || '/';

    if (path === '/health') {
      if (method !== 'GET') throw new HttpError(405, 'method not allowed');
      return send(res, 200, { status: 'ok' });
    }

    if (path === '/books') {
      if (method === 'GET') {
        const author = url.searchParams.get('author') ?? undefined;
        return send(res, 200, books.list(author));
      }
      if (method === 'POST') {
        const result = validateBook(await readJson(req));
        if (!result.ok) throw new HttpError(400, 'validation failed', result.errors);
        return send(res, 201, books.create(result.value));
      }
      throw new HttpError(405, 'method not allowed');
    }

    const match = /^\/books\/([^/]+)$/.exec(path);
    if (match) {
      const id = requireId(match[1]!);
      switch (method) {
        case 'GET': {
          const book = books.findById(id);
          if (!book) throw new HttpError(404, 'book not found');
          return send(res, 200, book);
        }
        case 'PUT': {
          const result = validateBook(await readJson(req));
          if (!result.ok) throw new HttpError(400, 'validation failed', result.errors);
          const book = books.update(id, result.value);
          if (!book) throw new HttpError(404, 'book not found');
          return send(res, 200, book);
        }
        case 'DELETE': {
          if (!books.delete(id)) throw new HttpError(404, 'book not found');
          return send(res, 204);
        }
        default:
          throw new HttpError(405, 'method not allowed');
      }
    }

    throw new HttpError(404, 'route not found');
  };

  return createServer((req, res) => {
    handle(req, res).catch((err: unknown) => {
      if (err instanceof HttpError) {
        sendError(res, err.status, err.message, err.details);
      } else {
        console.error(err);
        sendError(res, 500, 'internal server error');
      }
    });
  });
}
