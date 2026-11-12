import express, { type Express, type NextFunction, type Request, type Response } from "express";
import { BookStore, type BookInput } from "./db.js";

/** Validates a request body; returns the normalized book or a list of errors. */
export function validateBook(body: unknown): { value?: BookInput; errors: string[] } {
  const errors: string[] = [];
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { errors: ["request body must be a JSON object"] };
  }
  const { title, author, year, isbn } = body as Record<string, unknown>;
  if (typeof title !== "string" || title.trim() === "") errors.push("title is required");
  if (typeof author !== "string" || author.trim() === "") errors.push("author is required");
  if (year !== undefined && year !== null && (typeof year !== "number" || !Number.isInteger(year))) {
    errors.push("year must be an integer");
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }
  if (errors.length) return { errors };
  return {
    errors,
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: (year as number | null | undefined) ?? null,
      isbn: (isbn as string | null | undefined) ?? null,
    },
  };
}

function parseId(raw: string): number | undefined {
  return /^\d+$/.test(raw) ? Number(raw) : undefined;
}

export function createApp(store: BookStore): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const { value, errors } = validateBook(req.body);
    if (!value) return void res.status(400).json({ error: "validation failed", details: errors });
    res.status(201).json(store.create(value));
  });

  app.get("/books", (req, res) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    res.json(store.list(author));
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    const book = id === undefined ? undefined : store.get(id);
    if (!book) return void res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined || !store.get(id)) return void res.status(404).json({ error: "book not found" });
    const { value, errors } = validateBook(req.body);
    if (!value) return void res.status(400).json({ error: "validation failed", details: errors });
    res.json(store.update(id, value));
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined || !store.delete(id)) return void res.status(404).json({ error: "book not found" });
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "not found" });
  });

  app.use((err: { status?: number; type?: string }, _req: Request, res: Response, _next: NextFunction) => {
    if (err.type === "entity.parse.failed") return void res.status(400).json({ error: "invalid JSON" });
    const status = err.status && err.status >= 400 && err.status < 500 ? err.status : 500;
    res.status(status).json({ error: status === 500 ? "internal server error" : "bad request" });
  });

  return app;
}
