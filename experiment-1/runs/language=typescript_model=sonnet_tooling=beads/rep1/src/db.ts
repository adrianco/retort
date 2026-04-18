import Database from 'better-sqlite3';
import path from 'path';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export function createDb(dbPath?: string): Database.Database {
  const resolvedPath = dbPath ?? path.join(process.cwd(), 'books.db');
  const db = new Database(resolvedPath);

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);

  return db;
}
