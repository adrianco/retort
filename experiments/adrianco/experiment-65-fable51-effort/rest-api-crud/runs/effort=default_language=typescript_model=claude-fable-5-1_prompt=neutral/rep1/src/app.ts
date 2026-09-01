import express, {
  type Express,
  type NextFunction,
  type Request,
  type Response,
} from "express";
import type { DatabaseSync } from "node:sqlite";
import { BookRepository, DuplicateIsbnError } from "./db.js";
import { parseId, validateBookInput } from "./validation.js";

/** Builds the Express application on top of an already-opened SQLite database. */
export function createApp(db: DatabaseSync): Express {
  const app = express();
  const books = new BookRepository(db);

  app.disable("x-powered-by");
  app.use(express.json({ limit: "100kb" }));

  app.get("/health", (_req, res) => {
    try {
      db.prepare("SELECT 1").get();
      res.status(200).json({ status: "ok", database: "ok" });
    } catch {
      res.status(503).json({ status: "degraded", database: "unavailable" });
    }
  });

  app.post("/books", (req, res) => {
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.errors });
      return;
    }
    const book = books.create(result.value);
    res.status(201).location(`/books/${book.id}`).json(book);
  });

  app.get("/books", (req, res) => {
    const rawAuthor = req.query.author;
    let author: string | undefined;
    if (rawAuthor !== undefined) {
      if (typeof rawAuthor !== "string") {
        res.status(400).json({
          error: "Validation failed",
          details: [{ field: "author", message: "author filter must be a single string" }],
        });
        return;
      }
      author = rawAuthor.trim();
    }
    res.status(200).json(books.list(author));
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const book = books.get(id);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    const result = validateBookInput(req.body);
    if (!result.ok) {
      res.status(400).json({ error: "Validation failed", details: result.errors });
      return;
    }
    const book = books.update(id, result.value);
    if (!book) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(200).json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === undefined) {
      res.status(400).json({ error: "Invalid book id" });
      return;
    }
    if (!books.delete(id)) {
      res.status(404).json({ error: "Book not found" });
      return;
    }
    res.status(204).send();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "Not found" });
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof DuplicateIsbnError) {
      res.status(409).json({ error: err.message });
      return;
    }
    const e = err as { type?: string; status?: number; message?: string };
    if (e.type === "entity.parse.failed") {
      res.status(400).json({ error: "Malformed JSON body" });
      return;
    }
    if (e.type === "entity.too.large") {
      res.status(413).json({ error: "Request body too large" });
      return;
    }
    if (typeof e.status === "number" && e.status >= 400 && e.status < 500) {
      res.status(e.status).json({ error: e.message ?? "Bad request" });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  });

  return app;
}
