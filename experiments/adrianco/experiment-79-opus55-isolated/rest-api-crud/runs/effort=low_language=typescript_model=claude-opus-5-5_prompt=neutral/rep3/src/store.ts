import { DatabaseSync } from "node:sqlite";
import type { BookInput } from "./validation.ts";

export interface Book extends BookInput {
  id: number;
}

const COLUMNS = "id, title, author, year, isbn";

/** SQLite-backed book storage. Pass ":memory:" for an ephemeral database. */
export class BookStore {
  private readonly db: DatabaseSync;

  constructor(path: string) {
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
    const row = this.db
      .prepare(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING ${COLUMNS}`)
      .get(input.title, input.author, input.year, input.isbn);
    return row as unknown as Book;
  }

  /** Lists books ordered by id; the author filter is an exact, case-insensitive match. */
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
    return this.db.prepare(`SELECT ${COLUMNS} FROM books WHERE id = ?`).get(id) as unknown as Book | undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const row = this.db
      .prepare(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING ${COLUMNS}`)
      .get(input.title, input.author, input.year, input.isbn, id);
    return row as unknown as Book | undefined;
  }

  delete(id: number): boolean {
    return this.db.prepare("DELETE FROM books WHERE id = ?").run(id).changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
