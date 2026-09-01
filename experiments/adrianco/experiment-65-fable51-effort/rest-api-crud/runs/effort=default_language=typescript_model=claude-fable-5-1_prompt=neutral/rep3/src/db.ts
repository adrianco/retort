import { DatabaseSync } from "node:sqlite";
import type { Book, BookInput } from "./types.js";

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER,
    isbn       TEXT,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  );
  CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`;

export class BookRepository {
  private readonly db: DatabaseSync;

  /**
   * @param path SQLite file path, or ":memory:" for an in-memory database.
   */
  constructor(path: string) {
    this.db = new DatabaseSync(path);
    this.db.exec("PRAGMA journal_mode = WAL;");
    this.db.exec("PRAGMA foreign_keys = ON;");
    this.db.exec(SCHEMA);
  }

  list(filter: { author?: string } = {}): Book[] {
    if (filter.author !== undefined) {
      const stmt = this.db.prepare(
        "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
      );
      return stmt.all(filter.author) as unknown as Book[];
    }
    return this.db.prepare("SELECT * FROM books ORDER BY id").all() as unknown as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as unknown as
      | Book
      | undefined;
  }

  create(input: BookInput): Book {
    const result = this.db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(input.title, input.author, input.year, input.isbn);
    const created = this.get(Number(result.lastInsertRowid));
    if (!created) throw new Error("Failed to read back inserted book");
    return created;
  }

  update(id: number, input: BookInput): Book | undefined {
    const result = this.db
      .prepare(
        `UPDATE books
           SET title = ?, author = ?, year = ?, isbn = ?,
               updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
         WHERE id = ?`,
      )
      .run(input.title, input.author, input.year, input.isbn, id);
    if (result.changes === 0) return undefined;
    return this.get(id);
  }

  delete(id: number): boolean {
    const result = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return result.changes > 0;
  }

  /** Lightweight liveness probe used by the health endpoint. */
  ping(): boolean {
    const row = this.db.prepare("SELECT 1 AS ok").get() as { ok: number } | undefined;
    return row?.ok === 1;
  }

  close(): void {
    this.db.close();
  }
}
