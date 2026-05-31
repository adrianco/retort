import Database from "better-sqlite3";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type NewBook = Omit<Book, "id">;

/**
 * Create and initialize a database connection.
 * Pass ":memory:" for an ephemeral DB (used in tests), or a file path
 * for persistent storage (defaults to "books.db").
 */
export function createDb(filename = "books.db"): Database.Database {
  const db = new Database(filename);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT    NOT NULL,
      author TEXT    NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
  `);
  return db;
}

export class BookStore {
  constructor(private db: Database.Database) {}

  create(book: NewBook): Book {
    const info = this.db
      .prepare(
        `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
      )
      .run(book.title, book.author, book.year, book.isbn);
    return this.get(Number(info.lastInsertRowid))!;
  }

  list(author?: string): Book[] {
    if (author !== undefined) {
      return this.db
        .prepare(`SELECT * FROM books WHERE author = ? ORDER BY id`)
        .all(author) as Book[];
    }
    return this.db.prepare(`SELECT * FROM books ORDER BY id`).all() as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare(`SELECT * FROM books WHERE id = ?`).get(id) as
      | Book
      | undefined;
  }

  update(id: number, book: NewBook): Book | undefined {
    const info = this.db
      .prepare(
        `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
      )
      .run(book.title, book.author, book.year, book.isbn, id);
    if (info.changes === 0) return undefined;
    return this.get(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare(`DELETE FROM books WHERE id = ?`).run(id);
    return info.changes > 0;
  }
}
