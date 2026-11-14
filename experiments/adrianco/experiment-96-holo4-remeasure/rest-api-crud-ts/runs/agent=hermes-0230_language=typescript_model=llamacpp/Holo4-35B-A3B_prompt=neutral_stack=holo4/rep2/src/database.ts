import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.join(__dirname, '..', 'books.db');
const db: any = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
`);

export { db };
