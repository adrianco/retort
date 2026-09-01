import express, { type Express, type Request, type Response, type NextFunction } from "express";
import type { Db } from "./db";
import { validateBook, parseId } from "./validation";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function createApp(db: Db): Express {
  const app = express();
  app.use(express.json());

  const selectAll = db.prepare<[], Book>("SELECT * FROM books ORDER BY id");
  const selectByAuthor = db.prepare<[string], Book>(
    "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id"
  );
  const selectById = db.prepare<[number], Book>("SELECT * FROM books WHERE id = ?");
  const insert = db.prepare<[string, string, number | null, string | null]>(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const update = db.prepare<[string, string, number | null, string | null, number]>(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  );
  const remove = db.prepare<[number]>("DELETE FROM books WHERE id = ?");

  app.get("/health", (_req, res) => {
    try {
      db.prepare("SELECT 1").get();
      res.json({ status: "ok" });
    } catch {
      res.status(503).json({ status: "error" });
    }
  });

  app.post("/books", (req, res) => {
    const v = validateBook(req.body);
    if (!v.ok || !v.value) return res.status(400).json({ errors: v.errors });
    const { title, author, year, isbn } = v.value;
    const info = insert.run(title, author, year, isbn);
    const book = selectById.get(Number(info.lastInsertRowid));
    res.status(201).location(`/books/${book!.id}`).json(book);
  });

  app.get("/books", (req, res) => {
    const author = req.query.author;
    if (author !== undefined) {
      if (typeof author !== "string" || !author.trim()) {
        return res.status(400).json({ errors: ["author filter must be a non-empty string"] });
      }
      return res.json(selectByAuthor.all(author.trim()));
    }
    res.json(selectAll.all());
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(String(req.params.id));
    if (id === null) return res.status(400).json({ errors: ["id must be a positive integer"] });
    const book = selectById.get(id);
    if (!book) return res.status(404).json({ errors: ["book not found"] });
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(String(req.params.id));
    if (id === null) return res.status(400).json({ errors: ["id must be a positive integer"] });
    if (!selectById.get(id)) return res.status(404).json({ errors: ["book not found"] });
    const v = validateBook(req.body);
    if (!v.ok || !v.value) return res.status(400).json({ errors: v.errors });
    const { title, author, year, isbn } = v.value;
    update.run(title, author, year, isbn, id);
    res.json(selectById.get(id));
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(String(req.params.id));
    if (id === null) return res.status(400).json({ errors: ["id must be a positive integer"] });
    const info = remove.run(id);
    if (info.changes === 0) return res.status(404).json({ errors: ["book not found"] });
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ errors: ["route not found"] });
  });

  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const e = err as { type?: string; status?: number; message?: string };
    if (e?.type === "entity.parse.failed") {
      return res.status(400).json({ errors: ["invalid JSON body"] });
    }
    const status = typeof e?.status === "number" ? e.status : 500;
    res.status(status).json({ errors: [status === 500 ? "internal server error" : e.message ?? "error"] });
  });

  return app;
}
