import express, { type Express, type Request, type Response } from "express";
import type { DatabaseSync } from "node:sqlite";
import { BookRepository } from "./repository.js";
import { validateBook } from "./validation.js";

/**
 * Build the Express application around a given database connection.
 * Keeping the DB injectable lets tests run against an in-memory instance.
 */
export function createApp(db: DatabaseSync): Express {
  const app = express();
  app.use(express.json());

  const repo = new BookRepository(db);

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
    const book = repo.create(result.value!);
    return res.status(201).json(book);
  });

  // List books, optionally filtered by ?author=
  app.get("/books", (req: Request, res: Response) => {
    const author =
      typeof req.query.author === "string" ? req.query.author : undefined;
    const books = repo.findAll(author);
    return res.status(200).json(books);
  });

  // Get a single book by id
  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: "id must be a positive integer" });
    }
    const book = repo.findById(id);
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    return res.status(200).json(book);
  });

  // Update a book
  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: "id must be a positive integer" });
    }
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = repo.update(id, result.value!);
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    return res.status(200).json(book);
  });

  // Delete a book
  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: "id must be a positive integer" });
    }
    const deleted = repo.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: "Book not found" });
    }
    return res.status(204).send();
  });

  return app;
}

function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) {
    return null;
  }
  const id = Number(raw);
  return id > 0 ? id : null;
}
