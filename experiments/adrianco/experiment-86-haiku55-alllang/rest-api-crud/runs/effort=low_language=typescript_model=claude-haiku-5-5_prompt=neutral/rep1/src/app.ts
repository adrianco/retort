import http from 'node:http';
import { BookRepository } from './repository';
import { validateBookInput, type BookInput } from './book';

const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  constructor(public readonly status: number, message: string, public readonly details?: unknown) {
    super(message);
  }
}

function send(res: http.ServerResponse, status: number, body?: unknown): void {
  if (body === undefined) {
    res.writeHead(status);
    res.end();
    return;
  }
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function sendError(res: http.ServerResponse, status: number, message: string, details?: unknown): void {
  send(res, status, details === undefined ? { error: message } : { error: message, details });
}

function readJson(req: http.IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on('data', (chunk: Buffer) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new HttpError(413, 'Request body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || 'null'));
      } catch {
        reject(new HttpError(400, 'Malformed JSON body'));
      }
    });
    req.on('error', reject);
  });
}

/** Parses a positive integer path segment; returns null if it is not one. */
function parseId(segment: string): number | null {
  return /^[1-9]\d*$/.test(segment) ? Number(segment) : null;
}

/** Creates the HTTP request handler bound to the given repository. */
export function createHandler(repo: BookRepository): http.RequestListener {
  return async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const parts = url.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
      const method = req.method ?? 'GET';

      if (parts.length === 1 && parts[0] === 'health') {
        if (method !== 'GET') return sendError(res, 405, 'Method not allowed');
        let ok = true;
        try {
          repo.ping();
        } catch {
          ok = false;
        }
        return send(res, ok ? 200 : 503, { status: ok ? 'ok' : 'unavailable' });
      }

      if (parts.length === 1 && parts[0] === 'books') {
        if (method === 'GET') {
          const author = url.searchParams.get('author') ?? undefined;
          return send(res, 200, repo.findAll(author !== undefined ? { author } : {}));
        }
        if (method === 'POST') {
          const result = validateBookInput(await readJson(req));
          if (!result.ok) return sendError(res, 400, 'Validation failed', result.errors);
          // Create requires title and author, which validateBookInput enforces when not partial.
          return send(res, 201, repo.create(result.value as BookInput));
        }
        return sendError(res, 405, 'Method not allowed');
      }

      if (parts.length === 2 && parts[0] === 'books') {
        const id = parseId(parts[1]);
        if (id === null) return sendError(res, 400, 'Book id must be a positive integer');

        if (method === 'GET') {
          const book = repo.findById(id);
          return book ? send(res, 200, book) : sendError(res, 404, 'Book not found');
        }
        if (method === 'PUT') {
          const result = validateBookInput(await readJson(req), true);
          if (!result.ok) return sendError(res, 400, 'Validation failed', result.errors);
          const book = repo.update(id, result.value);
          return book ? send(res, 200, book) : sendError(res, 404, 'Book not found');
        }
        if (method === 'DELETE') {
          return repo.delete(id) ? send(res, 204) : sendError(res, 404, 'Book not found');
        }
        return sendError(res, 405, 'Method not allowed');
      }

      return sendError(res, 404, 'Not found');
    } catch (err) {
      if (err instanceof HttpError) return sendError(res, err.status, err.message, err.details);
      console.error(err);
      return sendError(res, 500, 'Internal server error');
    }
  };
}

export function createServer(repo: BookRepository): http.Server {
  return http.createServer(createHandler(repo));
}
