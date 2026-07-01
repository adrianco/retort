import express, { Express, Request, Response } from "express";
import { DatabaseSync } from "node:sqlite";
import { Book, BookInput } from "./types";
import { validateBookInput } from "./validation";

export function createApp(db: DatabaseSync): Express {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req: Request, res: Response) => {
    res.status(200).json({ status: "ok" });
  });

  app.post("/books", (req: Request, res: Response) => {
    const input = req.body as BookInput;
    const result = validateBookInput(input);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }

    const stmt = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const info = stmt.run(
      input.title as string,
      input.author as string,
      (input.year as number | undefined) ?? null,
      (input.isbn as string | undefined) ?? null
    );

    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(info.lastInsertRowid) as unknown as Book;
    res.status(201).json(book);
  });

  app.get("/books", (req: Request, res: Response) => {
    const { author } = req.query;
    let books: Book[];
    if (typeof author === "string") {
      books = db
        .prepare("SELECT * FROM books WHERE author = ?")
        .all(author) as unknown as Book[];
    } else {
      books = db.prepare("SELECT * FROM books").all() as unknown as Book[];
    }
    res.status(200).json(books);
  });

  app.get("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ errors: ["id must be an integer"] });
    }
    const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      unknown as Book | undefined;
    if (!book) {
      return res.status(404).json({ errors: ["book not found"] });
    }
    res.status(200).json(book);
  });

  app.put("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ errors: ["id must be an integer"] });
    }

    const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      unknown as Book | undefined;
    if (!existing) {
      return res.status(404).json({ errors: ["book not found"] });
    }

    const input = req.body as BookInput;
    const result = validateBookInput(input, { partial: true });
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }

    const updated: Book = {
      id,
      title: input.title !== undefined ? (input.title as string) : existing.title,
      author:
        input.author !== undefined ? (input.author as string) : existing.author,
      year:
        input.year !== undefined ? (input.year as number | null) : existing.year,
      isbn:
        input.isbn !== undefined ? (input.isbn as string | null) : existing.isbn,
    };

    db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    ).run(updated.title, updated.author, updated.year, updated.isbn, id);

    res.status(200).json(updated);
  });

  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id)) {
      return res.status(400).json({ errors: ["id must be an integer"] });
    }
    const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id);
    if (!existing) {
      return res.status(404).json({ errors: ["book not found"] });
    }
    db.prepare("DELETE FROM books WHERE id = ?").run(id);
    res.status(204).send();
  });

  return app;
}
