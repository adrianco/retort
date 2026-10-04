import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function createDatabase(filename = process.env.DATABASE_PATH ?? 'books.sqlite'): Database.Database {
  const db = new Database(filename);
  db.pragma('journal_mode = WAL');
  db.exec(`CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )`);
  return db;
}
