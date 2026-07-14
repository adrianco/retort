import { DatabaseSync } from 'node:sqlite';

export function createDb(path: string): DatabaseSync {
  const db = new DatabaseSync(path);

  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);

  return db;
}
