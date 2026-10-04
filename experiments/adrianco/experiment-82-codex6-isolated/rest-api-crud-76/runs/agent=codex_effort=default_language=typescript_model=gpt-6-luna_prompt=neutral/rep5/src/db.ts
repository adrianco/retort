import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function createDatabase(filename = process.env.DATABASE_PATH ?? 'books.sqlite'): DatabaseSync {
  const db = new DatabaseSync(filename);
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);
  return db;
}
