import sqlite3 from 'sqlite3';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'books.db');

function getDb(): sqlite3.Database {
  return new sqlite3.Database(DB_PATH);
}

export function run(sql: string, params: any[] = []): Promise<void> {
  return new Promise((resolve, reject) => {
    const db = getDb();
    db.run(sql, ...(params as any[]), (err: Error | null) => {
      db.close();
      if (err) reject(err);
      else resolve();
    });
  });
}

export function all<T>(sql: string, params: any[] = []): Promise<T[]> {
  return new Promise((resolve, reject) => {
    const db = getDb();
    db.all(sql, ...(params as any[]), (err: Error | null, rows: any[]) => {
      db.close();
      if (err) reject(err);
      else resolve(rows as T[]);
    });
  });
}

export function get<T>(sql: string, params: any[] = []): Promise<T | null> {
  return new Promise((resolve, reject) => {
    const db = getDb();
    db.get(sql, ...(params as any[]), (err: Error | null, row: any) => {
      db.close();
      if (err) reject(err);
      else resolve(row as T | null);
    });
  });
}

export function runWithLastInsertId(sql: string, params: any[] = []): Promise<{ lastInsertId: number }> {
  return new Promise((resolve, reject) => {
    const db = getDb();
    db.run(sql, ...(params as any[]), function (this: sqlite3.RunResult, err: Error | null) {
      db.close();
      if (err) reject(err);
      else resolve({ lastInsertId: this.lastID });
    });
  });
}

// Initialize the database
const initDb = getDb();
initDb.serialize(() => {
  initDb.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
});
initDb.close();
