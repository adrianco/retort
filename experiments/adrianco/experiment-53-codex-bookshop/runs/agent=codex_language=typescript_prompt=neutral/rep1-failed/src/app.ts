import express, { NextFunction, Request, Response } from "express";
import Database from "better-sqlite3";
import { rowToBook } from "./db";

type BookInput = { title?: unknown; author?: unknown; year?: unknown; isbn?: unknown };

function validateBookInput(body: BookInput, partial = false): string | null {
  if (!partial || body.title !== undefined) {
    if (typeof body.title !== "string" || body.title.trim() === "") return "title is required";
  }
  if (!partial || body.author !== undefined) {
    if (typeof body.author !== "string" || body.author.trim() === "") return "author is required";
  }
  if (body.year !== undefined && body.year !== null &&
      (!Number.isInteger(body.year) || (body.year as number) < 0)) return "year must be a non-negative integer";
  if (body.isbn !== undefined && body.isbn !== null && typeof body.isbn !== "string") return "isbn must be a string";
  return null;
}

function idFrom(request: Request): number | null {
  const id = Number(request.params.id);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function createApp(database: Database.Database) {
  const app = express();
  app.use(express.json());

  app.get("/health", (_request, response) => response.json({ status: "ok" }));

  app.post("/books", (request, response) => {
    const body = (request.body ?? {}) as BookInput;
    const error = validateBookInput(body);
    if (error) return response.status(400).json({ error });
    const result = database.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run((body.title as string).trim(), (body.author as string).trim(), body.year ?? null, body.isbn ?? null);
    const book = database.prepare("SELECT * FROM books WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>;
    return response.status(201).json(rowToBook(book));
  });

  app.get("/books", (request, response) => {
    const author = typeof request.query.author === "string" ? request.query.author : undefined;
    const rows = author === undefined
      ? database.prepare("SELECT * FROM books ORDER BY id").all()
      : database.prepare("SELECT * FROM books WHERE author = ? ORDER BY id").all(author);
    return response.json((rows as Record<string, unknown>[]).map(rowToBook));
  });

  app.get("/books/:id", (request, response) => {
    const id = idFrom(request);
    if (id === null) return response.status(400).json({ error: "id must be a positive integer" });
    const book = database.prepare("SELECT * FROM books WHERE id = ?").get(id) as Record<string, unknown> | undefined;
    return book ? response.json(rowToBook(book)) : response.status(404).json({ error: "book not found" });
  });

  app.put("/books/:id", (request, response) => {
    const id = idFrom(request);
    if (id === null) return response.status(400).json({ error: "id must be a positive integer" });
    const body = (request.body ?? {}) as BookInput;
    const error = validateBookInput(body, true);
    if (error) return response.status(400).json({ error });
    const current = database.prepare("SELECT * FROM books WHERE id = ?").get(id) as Record<string, unknown> | undefined;
    if (!current) return response.status(404).json({ error: "book not found" });
    const updated = {
      title: body.title === undefined ? current.title : (body.title as string).trim(),
      author: body.author === undefined ? current.author : (body.author as string).trim(),
      year: body.year === undefined ? current.year : body.year,
      isbn: body.isbn === undefined ? current.isbn : body.isbn,
    };
    database.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
      .run(updated.title, updated.author, updated.year, updated.isbn, id);
    return response.json(rowToBook(database.prepare("SELECT * FROM books WHERE id = ?").get(id) as Record<string, unknown>));
  });

  app.delete("/books/:id", (request, response) => {
    const id = idFrom(request);
    if (id === null) return response.status(400).json({ error: "id must be a positive integer" });
    const result = database.prepare("DELETE FROM books WHERE id = ?").run(id);
    return result.changes ? response.status(204).send() : response.status(404).json({ error: "book not found" });
  });

  app.use((_request, response) => response.status(404).json({ error: "not found" }));
  app.use((error: unknown, _request: Request, response: Response, _next: NextFunction) => {
    if (error instanceof SyntaxError) return response.status(400).json({ error: "invalid JSON" });
    return response.status(500).json({ error: "internal server error" });
  });
  return app;
}
