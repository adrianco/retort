import express, { type NextFunction, type Request, type Response } from "express";
import type { BookRepository } from "./db.js";
import { parseId, validateBookInput } from "./validation.js";

export function createApp(repo: BookRepository): express.Express {
  const app = express();
  app.disable("x-powered-by");
  app.use(express.json({ limit: "100kb" }));

  app.get("/health", (_req, res) => {
    const dbOk = repo.ping();
    res.status(dbOk ? 200 : 503).json({
      status: dbOk ? "ok" : "degraded",
      database: dbOk ? "ok" : "unavailable",
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
    });
  });

  app.get("/books", (req, res) => {
    const authorParam = req.query.author;
    if (authorParam !== undefined && typeof authorParam !== "string") {
      res.status(400).json({ error: "author filter must be a single string" });
      return;
    }
    const filter = authorParam !== undefined ? { author: authorParam.trim() } : {};
    res.json(repo.list(filter));
  });

  app.post("/books", (req, res) => {
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.errors });
      return;
    }
    const book = repo.create(result.value);
    res.status(201).location(`/books/${book.id}`).json(book);
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const book = repo.get(id);
    if (!book) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.errors });
      return;
    }
    const book = repo.update(id, result.value);
    if (!book) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    res.json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: "id must be a positive integer" });
      return;
    }
    if (!repo.delete(id)) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "Not found" });
  });

  // Error handler: malformed JSON from body-parser and any unexpected failures.
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const status =
      typeof err === "object" && err !== null && "status" in err && typeof err.status === "number"
        ? err.status
        : 500;
    if (status === 400) {
      res.status(400).json({ error: "Malformed JSON body" });
      return;
    }
    if (status === 413) {
      res.status(413).json({ error: "Request body too large" });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  });

  return app;
}
