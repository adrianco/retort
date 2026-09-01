import Database from 'better-sqlite3';
import type { Database as DatabaseType } from 'better-sqlite3';
import path from 'path';

const dbPath = path.join(__dirname, '..', 'books.db');
const db = new Database(dbPath) as unknown as DatabaseType;

// Enable WAL mode for better concurrent access
db.pragma('journal_mode = WAL');

// Create books table
db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
`);

export function initDatabase(): void {
  // Database is already initialized on module load
  // This function exists for explicit initialization if needed
}

export function getDb(): DatabaseType {
  return db;
}
