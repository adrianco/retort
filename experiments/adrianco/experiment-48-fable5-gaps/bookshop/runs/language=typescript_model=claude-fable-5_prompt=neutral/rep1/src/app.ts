import express, { type Express, type Request, type Response } from "express";
import type { DatabaseSync } from "node:sqlite";
import type { Book } from "./db.js";
import { validateBookInput } from "./validation.js";

export function createApp(db: DatabaseSync): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const result = validateBookInput(req.body);
    if (!result.ok || !result.value) {
      res.status(400).json({ errors: result.errors });
      return;
    }
    const { title, author, year, isbn } = result.value;
    const info = db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(title, author, year, isbn);
    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(info.lastInsertRowid as number) as unknown as Book;
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (typeof author === "string" && author !== "") {
      books = db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(author) as unknown as Book[];
    } else {
      books = db.prepare("SELECT * FROM books ORDER BY id").all() as unknown as Book[];
    }
    res.json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ errors: ["id must be a positive integer"] });
      return;
    }
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      | Book
      | undefined;
    if (!book) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ errors: ["id must be a positive integer"] });
      return;
    }
    const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
    if (!existing) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    const result = validateBookInput(req.body);
    if (!result.ok || !result.value) {
      res.status(400).json({ errors: result.errors });
      return;
    }
    const { title, author, year, isbn } = result.value;
    db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    ).run(title, author, year, isbn, id);
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as unknown as Book;
    res.json(book);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ errors: ["id must be a positive integer"] });
      return;
    }
    const info = db.prepare("DELETE FROM books WHERE id = ?").run(id);
    if (info.changes === 0) {
      res.status(404).json({ error: "book not found" });
      return;
    }
    res.status(204).end();
  });

  // Malformed JSON bodies from express.json() surface here.
  app.use(
    (err: Error, _req: Request, res: Response, next: express.NextFunction) => {
      if (err instanceof SyntaxError && "body" in err) {
        res.status(400).json({ errors: ["invalid JSON body"] });
        return;
      }
      next(err);
    }
  );

  return app;
}

function parseId(raw: string | string[] | undefined): number | null {
  if (typeof raw !== "string" || !/^\d+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
