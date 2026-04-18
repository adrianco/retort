import { DatabaseSync } from "node:sqlite";

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

export function createDb(path: string = ":memory:"): DatabaseSync {
  const db = new DatabaseSync(path);

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT    NOT NULL,
      author TEXT    NOT NULL,
      year   INTEGER,
      isbn   TEXT
    )
  `);

  return db;
}
