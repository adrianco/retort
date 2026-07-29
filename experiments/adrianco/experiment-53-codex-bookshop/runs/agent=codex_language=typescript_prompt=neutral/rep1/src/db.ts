import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

export type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

export function createDatabase(filename = process.env.DATABASE_PATH ?? "data/books.db"): Database.Database {
  if (filename !== ":memory:") fs.mkdirSync(path.dirname(path.resolve(filename)), { recursive: true });
  const database = new Database(filename);
  database.pragma("journal_mode = WAL");
  database.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return database;
}

export function rowToBook(row: Record<string, unknown>): Book {
  return {
    id: row.id as number,
    title: row.title as string,
    author: row.author as string,
    year: (row.year as number | null) ?? null,
    isbn: (row.isbn as string | null) ?? null,
  };
}
