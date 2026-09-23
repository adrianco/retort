import { createServer, IncomingMessage, ServerResponse, Server } from "node:http";
import { DatabaseSync } from "node:sqlite";

export interface Book { id: number; title: string; author: string; year: number | null; isbn: string | null }

function send(res: ServerResponse, status: number, body?: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(body === undefined ? "" : JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  let data = "";
  for await (const chunk of req) data += chunk;
  return data ? JSON.parse(data) : {};
}

export function validate(input: unknown): { book?: Omit<Book, "id">; errors: string[] } {
  const errors: string[] = [];
  if (typeof input !== "object" || input === null || Array.isArray(input)) return { errors: ["body must be a JSON object"] };
  const b = input as Record<string, unknown>;
  if (typeof b.title !== "string" || !b.title.trim()) errors.push("title is required");
  if (typeof b.author !== "string" || !b.author.trim()) errors.push("author is required");
  if (b.year != null && !Number.isInteger(b.year)) errors.push("year must be an integer");
  if (b.isbn != null && typeof b.isbn !== "string") errors.push("isbn must be a string");
  if (errors.length) return { errors };
  return {
    errors,
    book: { title: (b.title as string).trim(), author: (b.author as string).trim(), year: (b.year as number) ?? null, isbn: (b.isbn as string) ?? null },
  };
}

export function createApp(dbPath = ":memory:"): Server {
  const db = new DatabaseSync(dbPath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)`);
  const getById = (id: number) => db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;

  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://localhost");
      const path = url.pathname.replace(/\/+$/, "") || "/";
      const m = path.match(/^\/books\/(\d+)$/);

      if (path === "/health" && req.method === "GET") return send(res, 200, { status: "ok" });

      if (path === "/books") {
        if (req.method === "GET") {
          const author = url.searchParams.get("author");
          const rows = author
            ? db.prepare("SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id").all(author)
            : db.prepare("SELECT * FROM books ORDER BY id").all();
          return send(res, 200, rows);
        }
        if (req.method === "POST") {
          const { book, errors } = validate(await readJson(req));
          if (!book) return send(res, 400, { errors });
          const r = db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
            .run(book.title, book.author, book.year, book.isbn);
          return send(res, 201, getById(Number(r.lastInsertRowid)));
        }
        return send(res, 405, { error: "method not allowed" });
      }

      if (m) {
        const id = Number(m[1]);
        if (!getById(id)) return send(res, 404, { error: "book not found" });
        if (req.method === "GET") return send(res, 200, getById(id));
        if (req.method === "PUT") {
          const { book, errors } = validate(await readJson(req));
          if (!book) return send(res, 400, { errors });
          db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
            .run(book.title, book.author, book.year, book.isbn, id);
          return send(res, 200, getById(id));
        }
        if (req.method === "DELETE") {
          db.prepare("DELETE FROM books WHERE id = ?").run(id);
          res.writeHead(204).end();
          return;
        }
        return send(res, 405, { error: "method not allowed" });
      }
      send(res, 404, { error: "not found" });
    } catch (e) {
      if (e instanceof SyntaxError) return send(res, 400, { error: "invalid JSON" });
      send(res, 500, { error: "internal server error" });
    }
  });
  server.on("close", () => db.close());
  return server;
}
