import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import type { BookStore } from "./store.js";
import { validateBook } from "./validation.js";

const MAX_BODY_BYTES = 1024 * 1024;

class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly details?: string[],
  ) {
    super(message);
  }
}

function sendJson(res: ServerResponse, status: number, payload: unknown): void {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new HttpError(413, "request body too large");
    chunks.push(chunk as Buffer);
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

function methodNotAllowed(res: ServerResponse, allow: string): void {
  res.setHeader("Allow", allow);
  throw new HttpError(405, "method not allowed");
}

async function route(store: BookStore, req: IncomingMessage, res: ServerResponse): Promise<void> {
  const url = new URL(req.url ?? "/", "http://localhost");
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const method = req.method ?? "GET";

  if (path === "/health") {
    if (method !== "GET") return methodNotAllowed(res, "GET");
    return sendJson(res, 200, { status: "ok" });
  }

  if (path === "/books") {
    if (method === "GET") {
      const author = url.searchParams.get("author") ?? undefined;
      return sendJson(res, 200, store.list(author));
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
    const rawId = match[1] ?? "";
    if (!/^[1-9]\d{0,15}$/.test(rawId)) throw new HttpError(400, "book id must be a positive integer");
    const id = Number(rawId);
    const notFound = new HttpError(404, `book ${id} not found`);

    if (method === "GET") {
      const book = store.get(id);
      if (!book) throw notFound;
      return sendJson(res, 200, book);
    }
    if (method === "PUT") {
      const book = store.update(id, await readBook(req));
      if (!book) throw notFound;
      return sendJson(res, 200, book);
    }
    if (method === "DELETE") {
      if (!store.delete(id)) throw notFound;
      res.writeHead(204);
      res.end();
      return;
    }
    return methodNotAllowed(res, "GET, PUT, DELETE");
  }

  throw new HttpError(404, "not found");
}

export function createApp(store: BookStore): Server {
  return createServer((req, res) => {
    route(store, req, res).catch((err: unknown) => {
      if (err instanceof HttpError) {
        sendJson(res, err.status, { error: err.message, ...(err.details && { details: err.details }) });
      } else {
        console.error(err);
        sendJson(res, 500, { error: "internal server error" });
      }
    });
  });
}
