import { DatabaseSync } from "node:sqlite";
import type { BookInput } from "./validation.js";

export interface Book extends BookInput {
  id: number;
}

const COLUMNS = "id, title, author, year, isbn";

export class BookStore {
  private readonly db: DatabaseSync;

  /** @param path SQLite file path, or ":memory:" for an in-memory database. */
  constructor(path: string = ":memory:") {
    this.db = new DatabaseSync(path);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT
      )
    `);
  }

  create(input: BookInput): Book {
    const result = this.db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(input.title, input.author, input.year, input.isbn);
    return { id: Number(result.lastInsertRowid), ...input };
  }

  list(author?: string): Book[] {
    const rows =
      author === undefined
        ? this.db.prepare(`SELECT ${COLUMNS} FROM books ORDER BY id`).all()
        : this.db
            .prepare(`SELECT ${COLUMNS} FROM books WHERE author = ? COLLATE NOCASE ORDER BY id`)
            .all(author);
    return rows as unknown as Book[];
  }

  get(id: number): Book | undefined {
    const row = this.db.prepare(`SELECT ${COLUMNS} FROM books WHERE id = ?`).get(id);
    return row as unknown as Book | undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const result = this.db
      .prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
      .run(input.title, input.author, input.year, input.isbn, id);
    return result.changes === 0 ? undefined : { id, ...input };
  }

  delete(id: number): boolean {
    return this.db.prepare("DELETE FROM books WHERE id = ?").run(id).changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
