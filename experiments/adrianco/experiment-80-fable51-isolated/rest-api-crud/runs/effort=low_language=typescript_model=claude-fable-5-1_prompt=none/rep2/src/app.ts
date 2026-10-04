import { createServer } from "node:http";
import type { IncomingMessage, Server, ServerResponse } from "node:http";
import type { BookInput, BookStore } from "./db.ts";

const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  status: number;
  details?: string[];

  constructor(status: number, message: string, details?: string[]) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function send(res: ServerResponse, status: number, body?: unknown): void {
  if (body === undefined) {
    res.writeHead(status).end();
    return;
  }
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new HttpError(413, "Request body too large");
    chunks.push(chunk as Buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "Request body must be valid JSON");
  }
}

export function validateBook(body: unknown): BookInput {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    throw new HttpError(400, "Request body must be a JSON object");
  }
  const { title, author, year, isbn } = body as Record<string, unknown>;
  const errors: string[] = [];

  if (typeof title !== "string" || title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof author !== "string" || author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }
  if (year !== undefined && year !== null && !Number.isInteger(year)) {
    errors.push("year must be an integer");
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }
  if (errors.length > 0) throw new HttpError(400, "Validation failed", errors);

  return {
    title: (title as string).trim(),
    author: (author as string).trim(),
    year: (year as number | null | undefined) ?? null,
    isbn: (isbn as string | null | undefined) ?? null,
  };
}

function parseId(raw: string): number {
  if (!/^\d{1,15}$/.test(raw)) throw new HttpError(404, "Book not found");
  return Number(raw);
}

async function route(store: BookStore, req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? "/", "http://localhost");
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = req.method ?? "GET";

  if (path === "/health") {
    if (method !== "GET") throw new HttpError(405, "Method not allowed");
    return send(res, 200, { status: "ok" });
  }

  if (path === "/books") {
    if (method === "GET") {
      const author = url.searchParams.get("author");
      return send(res, 200, store.list(author ?? undefined));
    }
    if (method === "POST") {
      const book = store.create(validateBook(await readJson(req)));
      res.setHeader("Location", `/books/${book.id}`);
      return send(res, 201, book);
    }
    throw new HttpError(405, "Method not allowed");
  }

  const match = /^\/books\/([^/]+)$/.exec(path);
  if (match) {
    const id = parseId(match[1]!);
    if (method === "GET") {
      const book = store.get(id);
      if (!book) throw new HttpError(404, "Book not found");
      return send(res, 200, book);
    }
    if (method === "PUT") {
      const book = store.update(id, validateBook(await readJson(req)));
      if (!book) throw new HttpError(404, "Book not found");
      return send(res, 200, book);
    }
    if (method === "DELETE") {
      if (!store.delete(id)) throw new HttpError(404, "Book not found");
      return send(res, 204);
    }
    throw new HttpError(405, "Method not allowed");
  }

  throw new HttpError(404, "Not found");
}

export function createApp(store: BookStore): Server {
  return createServer((req, res) => {
    route(store, req, res).catch((err: unknown) => {
      if (err instanceof HttpError) {
        send(res, err.status, { error: err.message, ...(err.details && { details: err.details }) });
      } else {
        console.error(err);
        send(res, 500, { error: "Internal server error" });
      }
    });
  });
}
