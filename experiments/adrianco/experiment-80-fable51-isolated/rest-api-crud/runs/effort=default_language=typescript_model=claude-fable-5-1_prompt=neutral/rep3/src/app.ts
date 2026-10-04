import express, { type ErrorRequestHandler, type Express } from "express";
import type { BookStore } from "./db.js";
import { parseId, validateBook } from "./validation.js";

export function createApp(store: BookStore): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const result = validateBook(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "validation failed", details: result.errors });
      return;
    }
    const book = store.create(result.value);
    res.status(201).location(`/books/${book.id}`).json(book);
  });

  app.get("/books", (req, res) => {
    const { author } = req.query;
    if (author !== undefined && typeof author !== "string") {
      res.status(400).json({ error: "author filter must be a single string" });
      return;
    }
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
    if (!result.ok) {
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

  const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
    const status = typeof err?.status === "number" && err.status >= 400 && err.status < 500 ? err.status : 500;
    if (status === 500) console.error(err);
    const message = err?.type === "entity.parse.failed" ? "invalid JSON body"
      : status === 500 ? "internal server error"
      : String(err.message);
    res.status(status).json({ error: message });
  };
  app.use(errorHandler);

  return app;
}
