import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/**
 * Create and initialize a SQLite database.
 * Pass ':memory:' for an in-memory database (used by tests).
 */
export function createDb(filename: string = 'books.db'): Database.Database {
  const db = new Database(filename);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
  `);
  return db;
}
