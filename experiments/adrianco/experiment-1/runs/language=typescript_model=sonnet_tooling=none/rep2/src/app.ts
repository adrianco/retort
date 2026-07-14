import express, { Request, Response, NextFunction } from "express";
import { DatabaseSync } from "node:sqlite";
import { Book, BookInput } from "./db";

export function createApp(db: DatabaseSync): express.Application {
  const app = express();
  app.use(express.json());

  // Health check
  app.get("/health", (_req: Request, res: Response) => {
    res.json({ status: "ok" });
  });

  // POST /books — create a book
  app.post("/books", (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body as Partial<BookInput>;

    if (!title || typeof title !== "string" || title.trim() === "") {
      return res.status(400).json({ error: "title is required" });
    }
    if (!author || typeof author !== "string" || author.trim() === "") {
      return res.status(400).json({ error: "author is required" });
    }

    const stmt = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const result = stmt.run(
      title.trim(),
      author.trim(),
      year ?? null,
      isbn ?? null
    );

    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(result.lastInsertRowid) as unknown as Book;

    return res.status(201).json(book);
  });

  // GET /books — list all books, optional ?author= filter
  app.get("/books", (req: Request, res: Response) => {
    const { author } = req.query;

    let books: Book[];
    if (author && typeof author === "string") {
      books = db
        .prepare("SELECT * FROM books WHERE author LIKE ?")
        .all(`%${author}%`) as unknown as Book[];
    } else {
      books = db.prepare("SELECT * FROM books").all() as unknown as Book[];
    }

    return res.json(books);
  });

  // GET /books/:id — get a single book
  app.get("/books/:id", (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: "invalid id" });
    }

    const book = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(id) as unknown as Book | undefined;

    if (!book) {
      return res.status(404).json({ error: "book not found" });
    }

    return res.json(book);
  });

  // PUT /books/:id — update a book
  app.put("/books/:id", (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: "invalid id" });
    }

    const existing = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(id) as unknown as Book | undefined;

    if (!existing) {
      return res.status(404).json({ error: "book not found" });
    }

    const { title, author, year, isbn } = req.body as Partial<BookInput>;

    const newTitle = title !== undefined ? title.trim() : existing.title;
    const newAuthor = author !== undefined ? author.trim() : existing.author;

    if (newTitle === "") {
      return res.status(400).json({ error: "title cannot be empty" });
    }
    if (newAuthor === "") {
      return res.status(400).json({ error: "author cannot be empty" });
    }

    const newYear = year !== undefined ? year : existing.year;
    const newIsbn = isbn !== undefined ? isbn : existing.isbn;

    db.prepare(
      "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    ).run(newTitle, newAuthor, newYear, newIsbn, id);

    const updated = db
      .prepare("SELECT * FROM books WHERE id = ?")
      .get(id) as unknown as Book;

    return res.json(updated);
  });

  // DELETE /books/:id — delete a book
  app.delete("/books/:id", (req: Request, res: Response) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: "invalid id" });
    }

    const result = db.prepare("DELETE FROM books WHERE id = ?").run(id);

    if (result.changes === 0) {
      return res.status(404).json({ error: "book not found" });
    }

    return res.status(204).send();
  });

  // Generic error handler
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err);
    res.status(500).json({ error: "internal server error" });
  });

  return app;
}
