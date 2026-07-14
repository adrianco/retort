import express, { type Express } from "express";
import type Database from "better-sqlite3";
import {
  insertBook,
  listBooks,
  getBook,
  updateBook,
  deleteBook,
} from "./db.js";
import { validateBook } from "./book.js";

/**
 * Build an Express app wired to the given database. Keeping the db injectable
 * lets tests run against an in-memory database.
 */
export function createApp(db: Database.Database): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = insertBook(db, result.value!);
    res.status(201).json(book);
  });

  app.get("/books", (req, res) => {
    const author =
      typeof req.query.author === "string" ? req.query.author : undefined;
    res.json(listBooks(db, author));
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const book = getBook(db, id);
    if (!book) return res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = updateBook(db, id, result.value!);
    if (!book) return res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) return res.status(400).json({ error: "invalid id" });
    const deleted = deleteBook(db, id);
    if (!deleted) return res.status(404).json({ error: "book not found" });
    res.status(204).send();
  });

  return app;
}

function parseId(raw: string): number | null {
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}
