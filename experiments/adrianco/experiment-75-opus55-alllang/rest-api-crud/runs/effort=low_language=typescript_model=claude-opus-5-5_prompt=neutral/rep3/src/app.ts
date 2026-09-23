import express, { type NextFunction, type Request, type Response } from "express";
import { BookRepository } from "./db.js";
import { validateBook } from "./validate.js";

export function createApp(repo: BookRepository) {
  const app = express();
  app.use(express.json());

  const parseId = (req: Request, res: Response): number | undefined => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      res.status(400).json({ error: "invalid id" });
      return undefined;
    }
    return id;
  };

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/books", (req, res) => {
    const v = validateBook(req.body);
    if (!v.ok) return void res.status(400).json({ errors: v.errors });
    res.status(201).json(repo.create(v.value));
  });

  app.get("/books", (req, res) => {
    const author = typeof req.query.author === "string" ? req.query.author : undefined;
    res.json(repo.list(author));
  });

  app.get("/books/:id", (req, res) => {
    const id = parseId(req, res);
    if (id === undefined) return;
    const book = repo.get(id);
    if (!book) return void res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.put("/books/:id", (req, res) => {
    const id = parseId(req, res);
    if (id === undefined) return;
    const v = validateBook(req.body);
    if (!v.ok) return void res.status(400).json({ errors: v.errors });
    const book = repo.update(id, v.value);
    if (!book) return void res.status(404).json({ error: "book not found" });
    res.json(book);
  });

  app.delete("/books/:id", (req, res) => {
    const id = parseId(req, res);
    if (id === undefined) return;
    if (!repo.delete(id)) return void res.status(404).json({ error: "book not found" });
    res.status(204).end();
  });

  app.use((_req, res) => {
    res.status(404).json({ error: "not found" });
  });

  app.use((err: Error & { status?: number }, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status ?? 500;
    res.status(status).json({ error: status === 400 ? "malformed JSON" : "internal server error" });
  });

  return app;
}
