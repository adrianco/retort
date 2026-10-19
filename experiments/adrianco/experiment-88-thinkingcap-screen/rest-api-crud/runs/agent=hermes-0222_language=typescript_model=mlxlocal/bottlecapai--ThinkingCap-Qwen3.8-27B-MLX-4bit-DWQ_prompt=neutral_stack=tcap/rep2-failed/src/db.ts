import BetterSqlite3 from 'better-sqlite3';
import type { Database } from 'better-sqlite3';
import fs from 'node:fs';
import path from 'node:path';

const SCHEMA = `
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  year INTEGER,
  isbn TEXT
);
`;

/**
 * Open (and initialize) a SQLite database.
 * Pass ':memory:' for an in-memory database (used by tests).
 */
export function openDatabase(file: string): Database {
  if (file !== ':memory:') {
    fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
  }
  const db = new BetterSqlite3(file);
  db.pragma('journal_mode = WAL');
  db.exec(SCHEMA);
  return db;
}
