import express, { NextFunction, Request, Response } from "express";
import { BookInput, BookStore } from "./db";

type Validation = { value: BookInput } | { errors: string[] };

export function validateBook(body: unknown): Validation {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { errors: ["request body must be a JSON object"] };
  }
  const { title, author, year, isbn } = body as Record<string, unknown>;
  const errors: string[] = [];

  if (typeof title !== "string" || title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof author !== "string" || author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }
  if (year !== undefined && year !== null && !(typeof year === "number" && Number.isInteger(year))) {
    errors.push("year must be an integer");
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }
  if (errors.length > 0) return { errors };

  return {
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

export function createApp(store: BookStore) {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const result = validateBook(req.body);
    if ("errors" in result) {
      res.status(400).json({ error: "validation failed", details: result.errors });
      return;
    }
    res.status(201).json(store.create(result.value));
  });

  app.get("/books", (req, res) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    res.json(store.list(author));
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    const book = id === undefined ? undefined : store.get(id);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    const result = validateBook(req.body);
    if ("errors" in result) {
      res.status(400).json({ error: "validation failed", details: result.errors });
      return;
    }
    const book = store.update(id, result.value);
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined || !store.delete(id)) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "not found" });
  });

  app.use((err: Error & { status?: number }, _req: Request, res: Response, _next: NextFunction) => {
    if (err.status && err.status >= 400 && err.status < 500) {
      res.status(err.status).json({ error: "invalid request body" });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "internal server error" });
  });

  return app;
}
