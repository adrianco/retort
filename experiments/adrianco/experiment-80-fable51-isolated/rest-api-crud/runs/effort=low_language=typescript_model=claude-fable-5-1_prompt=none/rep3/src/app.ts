import express, { type Express, type NextFunction, type Request, type Response } from "express";
import { DatabaseSync } from "node:sqlite";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type BookInput = Omit<Book, "id">;

function validate(body: unknown): { errors: string[]; value?: BookInput } {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { errors: ["request body must be a JSON object"] };
  }
  const { title, author, year, isbn } = body as Record<string, unknown>;
  const errors: string[] = [];
  if (typeof title !== "string" || title.trim() === "") errors.push("title is required");
  if (typeof author !== "string" || author.trim() === "") errors.push("author is required");
  if (year !== undefined && year !== null && !Number.isInteger(year)) errors.push("year must be an integer");
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") errors.push("isbn must be a string");
  if (errors.length > 0) return { errors };
  return {
    errors,
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: (year as number | null | undefined) ?? null,
      isbn: (isbn as string | null | undefined) ?? null,
    },
  };
}

function parseId(raw: string): number | null {
  return /^\d+$/.test(raw) ? Number(raw) : null;
}

export function createApp(dbPath = ":memory:"): Express {
  const db = new DatabaseSync(dbPath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);

  const getBook = (id: number) =>
    db.prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?").get(id) as Book | undefined;

  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const { errors, value } = validate(req.body);
    if (!value) return void res.status(400).json({ error: "validation failed", details: errors });
    const result = db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(value.title, value.author, value.year, value.isbn);
    res.status(201).json(getBook(Number(result.lastInsertRowid)));
  });

  app.get("/books", (req, res) => {
    const author = req.query.author;
    const books =
      typeof author === "string"
        ? db.prepare("SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id").all(author)
        : db.prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id").all();
    res.json(books);
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    const book = id === null ? undefined : getBook(id);
    if (!book) return void res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    if (id === null || !getBook(id)) return void res.status(404).json({ error: "book not found" });
    const { errors, value } = validate(req.body);
    if (!value) return void res.status(400).json({ error: "validation failed", details: errors });
    db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?").run(
      value.title,
      value.author,
      value.year,
      value.isbn,
      id,
    );
    res.json(getBook(id));
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req.params.id);
    const changes = id === null ? 0 : db.prepare("DELETE FROM books WHERE id = ?").run(id).changes;
    if (changes === 0) return void res.status(404).json({ error: "book not found" });
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "not found" });
  });

  app.use((err: Error & { status?: number }, _req: Request, res: Response, _next: NextFunction) => {
    if (err.status && err.status >= 400 && err.status < 500) {
      return void res.status(err.status).json({ error: "invalid request body" });
    }
    console.error(err);
    res.status(500).json({ error: "internal server error" });
  });

  return app;
}
