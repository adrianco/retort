import type { DatabaseSync } from "node:sqlite";
import type { Book, BookInput } from "./db.js";

/**
 * Data-access layer for books. Wraps prepared statements over a SQLite DB.
 */
export class BookRepository {
  constructor(private readonly db: DatabaseSync) {}

  create(input: BookInput): Book {
    const stmt = this.db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    );
    const result = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.findById(Number(result.lastInsertRowid))!;
  }

  findAll(authorFilter?: string): Book[] {
    if (authorFilter) {
      return this.db
        .prepare("SELECT * FROM books WHERE author = ? ORDER BY id")
        .all(authorFilter) as unknown as Book[];
    }
    return this.db
      .prepare("SELECT * FROM books ORDER BY id")
      .all() as unknown as Book[];
  }

  findById(id: number): Book | undefined {
    return this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as
      | Book
      | undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const existing = this.findById(id);
    if (!existing) {
      return undefined;
    }
    this.db
      .prepare(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
      )
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
    return this.findById(id);
  }

  delete(id: number): boolean {
    const result = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return Number(result.changes) > 0;
  }
}
