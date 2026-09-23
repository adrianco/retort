import http from "node:http";
import { DatabaseSync } from "node:sqlite";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

type Input = { title?: unknown; author?: unknown; year?: unknown; isbn?: unknown };

function validate(body: unknown): { errors: string[]; data?: Omit<Book, "id"> } {
  const errors: string[] = [];
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { errors: ["body must be a JSON object"] };
  }
  const b = body as Input;
  if (typeof b.title !== "string" || !b.title.trim()) errors.push("title is required");
  if (typeof b.author !== "string" || !b.author.trim()) errors.push("author is required");
  if (b.year !== undefined && b.year !== null && !Number.isInteger(b.year)) errors.push("year must be an integer");
  if (b.isbn !== undefined && b.isbn !== null && typeof b.isbn !== "string") errors.push("isbn must be a string");
  if (errors.length) return { errors };
  return {
    errors,
    data: {
      title: (b.title as string).trim(),
      author: (b.author as string).trim(),
      year: (b.year as number | undefined) ?? null,
      isbn: (b.isbn as string | undefined) ?? null,
    },
  };
}

export function createApp(dbPath = ":memory:"): http.Server {
  const db = new DatabaseSync(dbPath);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)`);

  const send = (res: http.ServerResponse, status: number, payload?: unknown) => {
    if (payload === undefined) { res.writeHead(status).end(); return; }
    res.writeHead(status, { "Content-Type": "application/json" }).end(JSON.stringify(payload));
  };
  const readBody = (req: http.IncomingMessage) =>
    new Promise<unknown>((resolve, reject) => {
      let raw = "";
      req.on("data", (c) => { raw += c; if (raw.length > 1e6) req.destroy(); });
      req.on("end", () => { try { resolve(raw ? JSON.parse(raw) : undefined); } catch { reject(new Error("bad json")); } });
      req.on("error", reject);
    });
  const getBook = (id: number) =>
    db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;

  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://localhost");
      const path = url.pathname.replace(/\/+$/, "") || "/";
      const method = req.method ?? "GET";

      if (path === "/health" && method === "GET") return send(res, 200, { status: "ok" });

      if (path === "/books") {
        if (method === "GET") {
          const author = url.searchParams.get("author");
          const rows = author
            ? db.prepare("SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id").all(author)
            : db.prepare("SELECT * FROM books ORDER BY id").all();
          return send(res, 200, rows);
        }
        if (method === "POST") {
          let body: unknown;
          try { body = await readBody(req); } catch { return send(res, 400, { error: "invalid JSON" }); }
          const { errors, data } = validate(body);
          if (!data) return send(res, 400, { error: "validation failed", details: errors });
          const r = db.prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
            .run(data.title, data.author, data.year, data.isbn);
          return send(res, 201, getBook(Number(r.lastInsertRowid)));
        }
        return send(res, 405, { error: "method not allowed" });
      }

      const m = path.match(/^\/books\/([^/]+)$/);
      if (m) {
        const id = Number(m[1]);
        if (!Number.isInteger(id) || id <= 0) return send(res, 400, { error: "invalid id" });
        if (method === "GET") {
          const book = getBook(id);
          return book ? send(res, 200, book) : send(res, 404, { error: "book not found" });
        }
        if (method === "PUT") {
          let body: unknown;
          try { body = await readBody(req); } catch { return send(res, 400, { error: "invalid JSON" }); }
          const { errors, data } = validate(body);
          if (!data) return send(res, 400, { error: "validation failed", details: errors });
          if (!getBook(id)) return send(res, 404, { error: "book not found" });
          db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
            .run(data.title, data.author, data.year, data.isbn, id);
          return send(res, 200, getBook(id));
        }
        if (method === "DELETE") {
          const r = db.prepare("DELETE FROM books WHERE id = ?").run(id);
          return r.changes ? send(res, 204) : send(res, 404, { error: "book not found" });
        }
        return send(res, 405, { error: "method not allowed" });
      }

      send(res, 404, { error: "not found" });
    } catch (err) {
      send(res, 500, { error: "internal server error" });
    }
  });
  server.on("close", () => db.close());
  return server;
}
