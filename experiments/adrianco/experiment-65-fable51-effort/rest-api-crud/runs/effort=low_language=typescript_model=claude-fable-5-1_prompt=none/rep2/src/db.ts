import Database from "better-sqlite3";

export type Db = Database.Database;

export function createDb(path: string = ":memory:"): Db {
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
  `);
  return db;
}
