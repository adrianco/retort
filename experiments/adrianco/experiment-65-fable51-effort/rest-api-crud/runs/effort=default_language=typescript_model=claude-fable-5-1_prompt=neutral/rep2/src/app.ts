import express, { type Express, type NextFunction, type Request, type Response } from "express";
import type { DatabaseSync } from "node:sqlite";
import { ZodError } from "zod";
import { BookRepository, DuplicateIsbnError } from "./repository.js";
import {
  createBookSchema,
  formatZodError,
  idParamSchema,
  listQuerySchema,
  updateBookSchema,
} from "./validation.js";

export function createApp(db: DatabaseSync): Express {
  const app = express();
  const books = new BookRepository(db);

  app.disable("x-powered-by");
  app.use(express.json({ limit: "100kb" }));

  app.get("/health", (_req, res) => {
    try {
      db.prepare("SELECT 1").get();
      res.status(200).json({ status: "ok", database: "ok", timestamp: new Date().toISOString() });
    } catch {
      res.status(503).json({ status: "degraded", database: "unavailable", timestamp: new Date().toISOString() });
    }
  });

  app.post("/books", (req, res) => {
    const input = createBookSchema.parse(req.body ?? {});
    const book = books.create(input);
    res.status(201).location(`/books/${book.id}`).json(book);
  });

  app.get("/books", (req, res) => {
    const query = listQuerySchema.parse(req.query);
    const result = books.findAll({ author: query.author });
    res.status(200).json(result);
  });

  app.get("/books/:id", (req, res) => {
    const id = idParamSchema.parse(req.params.id);
    const book = books.findById(id);
    if (!book) {
      res.status(404).json({ error: "Not Found", message: `Book ${id} not found` });
      return;
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = idParamSchema.parse(req.params.id);
    const input = updateBookSchema.parse(req.body ?? {});
    const book = books.update(id, input);
    if (!book) {
      res.status(404).json({ error: "Not Found", message: `Book ${id} not found` });
      return;
    }
    res.status(200).json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = idParamSchema.parse(req.params.id);
    if (!books.delete(id)) {
      res.status(404).json({ error: "Not Found", message: `Book ${id} not found` });
      return;
    }
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "Not Found", message: "Route not found" });
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ZodError) {
      res.status(400).json({ error: "Validation Error", details: formatZodError(err) });
      return;
    }
    if (err instanceof DuplicateIsbnError) {
      res.status(409).json({ error: "Conflict", message: err.message });
      return;
    }
    // Malformed JSON body (body-parser sets type/status).
    const maybeHttp = err as { type?: string; status?: number; message?: string };
    if (maybeHttp.type === "entity.parse.failed") {
      res.status(400).json({ error: "Bad Request", message: "Request body is not valid JSON" });
      return;
    }
    if (maybeHttp.type === "entity.too.large") {
      res.status(413).json({ error: "Payload Too Large", message: "Request body exceeds the size limit" });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "Internal Server Error" });
  });

  return app;
}
