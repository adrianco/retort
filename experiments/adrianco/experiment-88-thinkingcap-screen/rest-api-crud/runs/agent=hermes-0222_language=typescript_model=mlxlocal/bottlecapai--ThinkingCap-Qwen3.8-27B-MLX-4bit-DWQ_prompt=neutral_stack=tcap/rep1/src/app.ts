import express, {
  type Express,
  type NextFunction,
  type Request,
  type Response,
} from "express";
import type Database from "better-sqlite3";
import { createDb, type Book } from "./db.js";

/**
 * Validation errors carry an HTTP status of 400.
 */
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

/** Validate fields for POST /books. All of title/author/year/isbn must be present. */
function validateCreate(body: unknown): {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
} {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    throw new ValidationError("Request body must be a JSON object");
  }
  const data = body as Record<string, unknown>;

  if (!isNonEmptyString(data.title)) {
    throw new ValidationError("title is required and must be a non-empty string");
  }
  if (!isNonEmptyString(data.author)) {
    throw new ValidationError("author is required and must be a non-empty string");
  }
  if (data.year !== undefined && data.year !== null && !isInteger(data.year)) {
    throw new ValidationError("year must be an integer when provided");
  }
  if (data.isbn !== undefined && data.isbn !== null && typeof data.isbn !== "string") {
    throw new ValidationError("isbn must be a string when provided");
  }

  return {
    title: data.title.trim(),
    author: data.author.trim(),
    year: data.year === undefined || data.year === null ? null : (data.year as number),
    isbn:
      data.isbn === undefined || data.isbn === null || (data.isbn as string).trim() === ""
        ? null
        : (data.isbn as string).trim(),
  };
}

/**
 * Validate fields for PUT /books/:id. Any subset of title/author/year/isbn may be
 * provided; at least one must be. title/author must be non-empty when present.
 */
function validateUpdate(body: unknown): {
  title?: string;
  author?: string;
  year?: number | null;
  isbn?: string | null;
} {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    throw new ValidationError("Request body must be a JSON object");
  }
  const data = body as Record<string, unknown>;

  const fields: {
    title?: string;
    author?: string;
    year?: number | null;
    isbn?: string | null;
  } = {};

  if (data.title !== undefined) {
    if (!isNonEmptyString(data.title)) {
      throw new ValidationError("title must be a non-empty string when provided");
    }
    fields.title = data.title.trim();
  }
  if (data.author !== undefined) {
    if (!isNonEmptyString(data.author)) {
      throw new ValidationError("author must be a non-empty string when provided");
    }
    fields.author = data.author.trim();
  }
  if (data.year !== undefined) {
    if (data.year === null) {
      fields.year = null;
    } else if (!isInteger(data.year)) {
      throw new ValidationError("year must be an integer or null when provided");
    } else {
      fields.year = data.year;
    }
  }
  if (data.isbn !== undefined) {
    if (data.isbn === null) {
      fields.isbn = null;
    } else if (typeof data.isbn !== "string") {
      throw new ValidationError("isbn must be a string or null when provided");
    } else {
      fields.isbn = data.isbn.trim() === "" ? null : data.isbn.trim();
    }
  }

  if (Object.keys(fields).length === 0) {
    throw new ValidationError(
      "Request body must contain at least one of: title, author, year, isbn"
    );
  }

  return fields;
}

function parseId(raw: string | string[] | undefined): number {
  if (typeof raw !== "string" || !/^\d+$/.test(raw)) {
    throw new ValidationError("id must be a positive integer");
  }
  return Number(raw);
}

function rowToBook(row: {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
  };
}

/**
 * Build the Express app.
 *
 * @param dbPath Path to the SQLite file, or ":memory:" for an in-memory DB (tests).
 */
export function createApp(dbPath: string = "books.db"): Express {
  const db: Database.Database = createDb(dbPath);
  const app = express();

  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const fields = validateCreate(req.body);
    const result = db
      .prepare(
        "INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn)"
      )
      .run(fields);
    const row = db
      .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
      .get(result.lastInsertRowid) as Book;
    res.status(201).json(rowToBook(row));
  });

  app.get("/books", (req: Request, res: Response) => {
    const author = req.query.author;
    let rows: Book[];
    if (typeof author === "string" && author.length > 0) {
      rows = db
        .prepare(
          "SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id"
        )
        .all(author) as Book[];
    } else {
      rows = db
        .prepare("SELECT id, title, author, year, isbn FROM books ORDER BY id")
        .all() as Book[];
    }
    res.status(200).json(rows.map(rowToBook));
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    const row = db
      .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
      .get(id) as Book | undefined;
    if (!row) {
      res.status(404).json({ error: `Book with id ${id} not found` });
      return;
    }
    res.status(200).json(rowToBook(row));
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    const existing = db
      .prepare("SELECT id FROM books WHERE id = ?")
      .get(id) as { id: number } | undefined;
    if (!existing) {
      res.status(404).json({ error: `Book with id ${id} not found` });
      return;
    }

    const fields = validateUpdate(req.body);
    const sets: string[] = [];
    const params: Record<string, unknown> = { id };
    for (const [key, value] of Object.entries(fields)) {
      sets.push(`${key} = @${key}`);
      params[key] = value;
    }
    db.prepare(`UPDATE books SET ${sets.join(", ")} WHERE id = @id`).run(params);

    const row = db
      .prepare("SELECT id, title, author, year, isbn FROM books WHERE id = ?")
      .get(id) as Book;
    res.status(200).json(rowToBook(row));
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);
    if (result.changes === 0) {
      res.status(404).json({ error: `Book with id ${id} not found` });
      return;
    }
    res.status(204).send();
  });

  // JSON 404 for unknown routes.
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: "Not found" });
  });

  // JSON error handler (validation, malformed JSON, unexpected errors).
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    if (err instanceof ValidationError) {
      res.status(400).json({ error: err.message });
      return;
    }
    const anyErr = err as { status?: number; type?: string; message?: string };
    if (anyErr?.type === "entity.parse.failed") {
      res.status(400).json({ error: "Malformed JSON in request body" });
      return;
    }
    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  });

  return app;
}
