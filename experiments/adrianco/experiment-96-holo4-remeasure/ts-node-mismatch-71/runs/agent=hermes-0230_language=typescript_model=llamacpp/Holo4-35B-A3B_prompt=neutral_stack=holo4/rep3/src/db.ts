import Database from 'better-sqlite3';
import type { Database as DBType } from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'books.db');

const db: DBType = new Database(DB_PATH);

db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT UNIQUE
  )
`);

export { db };
