import Database from "better-sqlite3";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

/**
 * Create a database connection and ensure the schema exists.
 * Pass ":memory:" for an ephemeral in-memory database (used in tests).
 */
export function createDb(path: string = "books.db"): Database.Database {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
  return db;
}
