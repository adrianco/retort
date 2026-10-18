import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/**
 * Open (and initialize) a SQLite database.
 * Use ":memory:" for an in-memory database (tests).
 */
export function createDb(dbPath: string): Database.Database {
  if (dbPath !== ":memory:") {
    const dir = path.dirname(path.resolve(dbPath));
    fs.mkdirSync(dir, { recursive: true });
  }

  const db = new Database(dbPath);
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
