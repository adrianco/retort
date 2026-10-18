import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import type { BookRepository } from './db.js';
import { validateBook } from './validation.js';

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

/** Creates the HTTP server wired to the given repository. */
export function createApp(repo: BookRepository): Server {
  return createServer(async (req, res) => {
    try {
      await route(req, res, repo);
    } catch (err) {
      if (err instanceof HttpError) {
        sendJson(res, err.status, { error: err.message, ...(err.details ? { details: err.details } : {}) });
      } else if (err instanceof SyntaxError) {
        sendJson(res, 400, { error: 'Malformed JSON body' });
      } else {
        console.error(err);
        sendJson(res, 500, { error: 'Internal server error' });
      }
    }
  });
}

async function route(req: IncomingMessage, res: ServerResponse, repo: BookRepository): Promise<void> {
  const url = new URL(req.url ?? '/', 'http://localhost');
  const segments = url.pathname.split('/').filter(Boolean);
  const method = req.method ?? 'GET';

  if (segments.length === 1 && segments[0] === 'health') {
    if (method !== 'GET') throw methodNotAllowed(['GET']);
    sendJson(res, 200, { status: 'ok', database: repo.ping() ? 'up' : 'down' });
    return;
  }

  if (segments.length === 1 && segments[0] === 'books') {
    if (method === 'GET') {
      const author = url.searchParams.get('author') ?? undefined;
      sendJson(res, 200, repo.findAll(author));
      return;
    }
    if (method === 'POST') {
      const result = validateBook(await readJsonBody(req));
      if (!result.ok) throw validationError(result.errors);
      sendJson(res, 201, repo.create(result.value));
      return;
    }
    throw methodNotAllowed(['GET', 'POST']);
  }

  if (segments.length === 2 && segments[0] === 'books') {
    const id = parseId(segments[1]);
    if (id === undefined) throw new HttpError(404, 'Book not found');

    if (method === 'GET') {
      sendJson(res, 200, findOr404(repo, id));
      return;
    }
    if (method === 'PUT') {
      const result = validateBook(await readJsonBody(req));
      if (!result.ok) throw validationError(result.errors);
      const updated = repo.update(id, result.value);
      if (!updated) throw new HttpError(404, 'Book not found');
      sendJson(res, 200, updated);
      return;
    }
    if (method === 'DELETE') {
      if (!repo.delete(id)) throw new HttpError(404, 'Book not found');
      res.writeHead(204).end();
      return;
    }
    throw methodNotAllowed(['GET', 'PUT', 'DELETE']);
  }

  throw new HttpError(404, 'Not found');
}

/** Parses a positive integer path segment; returns undefined for anything else. */
function parseId(raw: string): number | undefined {
  if (!/^[1-9]\d*$/.test(raw)) return undefined;
  const id = Number(raw);
  return Number.isSafeInteger(id) ? id : undefined;
}

function findOr404(repo: BookRepository, id: number) {
  const book = repo.findById(id);
  if (!book) throw new HttpError(404, 'Book not found');
  return book;
}

function validationError(errors: Record<string, string>): HttpError {
  return new HttpError(400, 'Validation failed', errors);
}

function methodNotAllowed(allowed: string[]): HttpError {
  return new HttpError(405, `Method not allowed. Allowed: ${allowed.join(', ')}`);
}

async function readJsonBody(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new HttpError(413, 'Request body too large');
    chunks.push(chunk as Buffer);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  if (raw.trim() === '') throw new HttpError(400, 'Request body is required');
  return JSON.parse(raw);
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}
