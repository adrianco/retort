import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import type { BookStore } from "./store.ts";
import { validateBook } from "./validation.ts";

const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  readonly status: number;
  readonly details?: string[];

  constructor(status: number, message: string, details?: string[]) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
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
  for await (const chunk of req as AsyncIterable<Buffer>) {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) throw new HttpError(413, "request body too large");
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new HttpError(400, "request body must be valid JSON");
  }
}

async function readBook(req: IncomingMessage) {
  const result = validateBook(await readJson(req));
  if (!result.ok) throw new HttpError(400, "validation failed", result.errors);
  return result.value;
}

function parseId(raw: string): number {
  const id = Number(raw);
  if (!/^\d+$/.test(raw) || !Number.isSafeInteger(id) || id < 1) {
    throw new HttpError(400, "book id must be a positive integer");
  }
  return id;
}

function methodNotAllowed(res: ServerResponse, allow: string): void {
  res.setHeader("Allow", allow);
  throw new HttpError(405, "method not allowed");
}

async function route(store: BookStore, req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? "/", "http://localhost");
  const path = url.pathname.length > 1 ? url.pathname.replace(/\/+$/, "") : url.pathname;
  const method = req.method ?? "GET";

  if (path === "/health") {
    if (method !== "GET") return methodNotAllowed(res, "GET");
    return sendJson(res, 200, { status: "ok" });
  }

  if (path === "/books") {
    if (method === "GET") {
      const author = url.searchParams.get("author");
      return sendJson(res, 200, store.list(author === null || author === "" ? undefined : author));
    }
    if (method === "POST") {
      const book = store.create(await readBook(req));
      res.setHeader("Location", `/books/${book.id}`);
      return sendJson(res, 201, book);
    }
    return methodNotAllowed(res, "GET, POST");
  }

  const match = /^\/books\/([^/]+)$/.exec(path);
  if (match) {
    const id = parseId(match[1]!);
    if (method === "GET") {
      const book = store.get(id);
      if (!book) throw new HttpError(404, "book not found");
      return sendJson(res, 200, book);
    }
    if (method === "PUT") {
      const book = store.update(id, await readBook(req));
      if (!book) throw new HttpError(404, "book not found");
      return sendJson(res, 200, book);
    }
    if (method === "DELETE") {
      if (!store.delete(id)) throw new HttpError(404, "book not found");
      res.writeHead(204);
      res.end();
      return;
    }
    return methodNotAllowed(res, "GET, PUT, DELETE");
  }

  throw new HttpError(404, "not found");
}

/** Builds the HTTP server for the books API on top of the given store. */
export function createApp(store: BookStore): Server {
  return createServer((req, res) => {
    route(store, req, res).catch((err: unknown) => {
      if (err instanceof HttpError) {
        // An unread oversized body would otherwise be parsed as a second request.
        if (err.status === 413) res.setHeader("Connection", "close");
        sendJson(res, err.status, { error: err.message, ...(err.details && { details: err.details }) });
      } else {
        console.error(err);
        sendJson(res, 500, { error: "internal server error" });
      }
    });
  });
}
