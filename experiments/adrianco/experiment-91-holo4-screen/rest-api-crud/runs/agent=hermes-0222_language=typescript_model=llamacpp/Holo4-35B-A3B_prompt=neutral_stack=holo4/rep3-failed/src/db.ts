import Database, { type Database as SqliteDatabase } from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'books.db');

export const db: SqliteDatabase = new Database(DB_PATH);

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  );
`);
