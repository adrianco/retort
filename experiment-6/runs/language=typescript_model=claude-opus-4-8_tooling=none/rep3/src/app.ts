import express, { type Express, type Request, type Response } from "express";
import type Database from "better-sqlite3";
import { type Book, type BookInput } from "./db.ts";

/**
 * Validate the body of a create/update request.
 * Returns a list of human-readable error messages (empty if valid).
 */
function validateBookInput(body: unknown): { errors: string[]; value?: BookInput } {
  const errors: string[] = [];
  if (typeof body !== "object" || body === null) {
    return { errors: ["Request body must be a JSON object"] };
  }
  const b = body as Record<string, unknown>;

  if (typeof b.title !== "string" || b.title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof b.author !== "string" || b.author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== "number" || !Number.isInteger(b.year)) {
      errors.push("year must be an integer");
    }
  }
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== "string") {
      errors.push("isbn must be a string");
    }
  }

  if (errors.length > 0) return { errors };

  return {
    errors,
    value: {
      title: (b.title as string).trim(),
      author: (b.author as string).trim(),
      year: b.year === undefined ? null : (b.year as number | null),
      isbn: b.isbn === undefined ? null : (b.isbn as string | null),
    },
  };
}

export function createApp(db: Database.Database): Express {
  const app = express();
  app.use(express.json());

  // Health check
  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  // Create a book
  app.post("/books", (req: Request, res: Response) => {
    const { errors, value } = validateBookInput(req.body);
    if (errors.length > 0) {
      return res.status(400).json({ errors });
    }
    const info = db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(value!.title, value!.author, value!.year, value!.isbn);
    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(info.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  // List books, with optional ?author= filter
  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author;
    let books: Book[];
    if (typeof author === "string" && author.trim() !== "") {
      books = db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author) as Book[];
    } else {
      books = db.prepare("SELECT * FROM books ORDER BY id").all() as Book[];
    }
    res.status(200).json(books);
  });

  // Get a single book by ID
  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "id must be an integer" });
    }
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      | Book
      | undefined;
    if (!book) {
      return res.status(404).json({ error: "Book not found" });
    }
    res.status(200).json(book);
  });

  // Update a book
  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "id must be an integer" });
    }
    const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
    if (!existing) {
      return res.status(404).json({ error: "Book not found" });
    }
    const { errors, value } = validateBookInput(req.body);
    if (errors.length > 0) {
      return res.status(400).json({ errors });
    }
    db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    ).run(value!.title, value!.author, value!.year, value!.isbn, id);
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book;
    res.status(200).json(book);
  });

  // Delete a book
  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ error: "id must be an integer" });
    }
    const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
    if (info.changes === 0) {
      return res.status(404).json({ error: "Book not found" });
    }
    res.status(204).send();
  });

  return app;
}
