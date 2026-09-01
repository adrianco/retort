import type { Database } from 'better-sqlite3';
import path from 'path';

const dbPath = process.env.DATABASE_PATH || path.join(__dirname, '..', 'books.db');

let db: Database | null = null;

function getDb(): Database {
  if (!db) {
    const DatabaseModule = require('better-sqlite3');
    const newDb = new DatabaseModule(dbPath);
    newDb.pragma('journal_mode = WAL');
    newDb.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
    db = newDb;
  }
  return db!;
}

function resetDb(): void {
  if (db) {
    try { db.close(); } catch {}
    db = null;
  }
  if (dbPath) {
    const fs = require('fs');
    if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
    if (fs.existsSync(dbPath + '-wal')) fs.unlinkSync(dbPath + '-wal');
    if (fs.existsSync(dbPath + '-shm')) fs.unlinkSync(dbPath + '-shm');
  }
}

function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

export { getDb, resetDb, closeDb };
