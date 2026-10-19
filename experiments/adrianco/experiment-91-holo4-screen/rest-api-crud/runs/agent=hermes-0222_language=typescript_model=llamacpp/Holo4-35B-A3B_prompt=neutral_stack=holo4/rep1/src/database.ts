import Database from 'better-sqlite3';
import type { Database as DBType } from 'better-sqlite3';
import path from 'path';

let db: DBType | undefined;

function createDb(dbPath: string): DBType {
  const instance = new Database(dbPath);
  instance.pragma('journal_mode = WAL');
  instance.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
  return instance;
}

export function getDb(customPath?: string): DBType {
  if (!db) {
    if (customPath) {
      db = createDb(customPath);
    } else {
      const path = require('path');
      const dbPath = path.join(__dirname, '..', 'books.db');
      db = createDb(dbPath);
    }
  }
  return db;
}

export function resetDb() {
  if (db) {
    db.close();
    db = undefined;
  }
  // Remove the DB file so each test run starts fresh
  try {
    const fs = require('fs');
    const path = require('path');
    const dbPath = path.join(__dirname, '..', 'books.db');
    if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
    const walPath = dbPath + '-wal';
    if (fs.existsSync(walPath)) fs.unlinkSync(walPath);
    const shmPath = dbPath + '-shm';
    if (fs.existsSync(shmPath)) fs.unlinkSync(shmPath);
  } catch { /* ignore */ }
}