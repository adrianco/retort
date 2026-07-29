import express, { ErrorRequestHandler } from "express";
import Database from "better-sqlite3";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Partial<Pick<Book, "title" | "author" | "year" | "isbn">>;

function normalizeText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function validateInput(body: unknown, partial: boolean): { value?: BookInput; error?: string } {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { error: "Request body must be a JSON object" };
  }
  const input = body as Record<string, unknown>;
  const value: BookInput = {};
  if (input.title !== undefined) value.title = normalizeText(input.title);
  if (input.author !== undefined) value.author = normalizeText(input.author);
  if (input.year !== undefined && input.year !== null) {
    if (!Number.isInteger(input.year) || (input.year as number) < 0) return { error: "year must be a non-negative integer" };
    value.year = input.year as number;
  } else if (input.year === null) value.year = null;
  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string") return { error: "isbn must be a string or null" };
    value.isbn = input.isbn.trim();
  } else if (input.isbn === null) value.isbn = null;

  if (!partial && !value.title) return { error: "title is required" };
  if (!partial && !value.author) return { error: "author is required" };
  if (input.title !== undefined && !value.title) return { error: "title must be a non-empty string" };
  if (input.author !== undefined && !value.author) return { error: "author must be a non-empty string" };
  return { value };
}

export function createApp(databasePath = process.env.DATABASE_PATH ?? "./books.db") {
  const db = new Database(databasePath);
  db.pragma("journal_mode = WAL");
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => res.json({ status: "ok" }));

  app.post("/books", (req, res) => {
    const result = validateInput(req.body, false);
    if (result.error) return res.status(400).json({ error: result.error });
    const book = result.value!;
    const insert = db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)");
    const created = insert.run(book.title, book.author, book.year ?? null, book.isbn ?? null);
    const row = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").get(created.lastInsertRowid) as Book;
    return res.status(201).json(row);
  });

  app.get("/books", (req, res) => {
    const author = typeof req.query.author === "string" ? req.query.author.trim() : "";
    const rows = author
      ? db.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id").all(author)
      : db.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id").all();
    return res.json(rows);
  });

  app.get("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: "id must be a positive integer" });
    const book = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").get(id) as Book | undefined;
    return book ? res.json(book) : res.status(404).json({ error: "Book not found" });
  });

  app.put("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: "id must be a positive integer" });
    const current = db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").get(id) as Book | undefined;
    if (!current) return res.status(404).json({ error: "Book not found" });
    const result = validateInput(req.body, true);
    if (result.error) return res.status(400).json({ error: result.error });
    const next = { ...current, ...result.value };
    if (!next.title || !next.author) return res.status(400).json({ error: "title and author are required" });
    db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?").run(next.title, next.author, next.year, next.isbn, id);
    return res.json(db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").get(id));
  });

  app.delete("/books/:id", (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id < 1) return res.status(400).json({ error: "id must be a positive integer" });
    const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return result.changes ? res.status(204).send() : res.status(404).json({ error: "Book not found" });
  });

  const errors: ErrorRequestHandler = (error, _req, res, _next) => {
    if (error instanceof SyntaxError) return res.status(400).json({ error: "Request body must contain valid JSON" });
    return res.status(500).json({ error: "Internal server error" });
  };
  app.use(errors);
  (app as express.Express & { closeDatabase?: () => void }).closeDatabase = () => db.close();
  return app as express.Express & { closeDatabase: () => void };
}
