import express, { type Express, type Request, type Response } from "express";
import type Database from "better-sqlite3";
import { BookStore } from "./db.js";
import { validateBook } from "./validation.js";

/**
 * Build an Express app backed by the given database connection.
 * Keeping construction separate from the listening server lets tests
 * inject an in-memory database.
 */
export function createApp(db: Database.Database): Express {
  const app = express();
  app.use(express.json());

  const store = new BookStore(db);

  // Health check
  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  // Create a book
  app.post("/books", (req: Request, res: Response) => {
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = store.create(result.value!);
    res.status(201).json(book);
  });

  // List all books, optional ?author= filter
  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author;
    if (author !== undefined && typeof author !== "string") {
      return res.status(400).json({ errors: ["author filter must be a string"] });
    }
    res.status(200).json(store.list(author));
  });

  // Get a single book
  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ["id must be a positive integer"] });
    }
    const book = store.get(id);
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    res.status(200).json(book);
  });

  // Update a book
  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ["id must be a positive integer"] });
    }
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = store.update(id, result.value!);
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    res.status(200).json(book);
  });

  // Delete a book
  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ errors: ["id must be a positive integer"] });
    }
    const deleted = store.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: "Book not found" });
    }
    res.status(204).send();
  });

  return app;
}

function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const id = Number(raw);
  return id > 0 ? id : null;
}
