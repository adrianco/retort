import path from 'path';

// Simple SQLite wrapper without heavy typing
const dbPath = path.join(process.cwd(), 'books.db');
let db: any;

try {
  const Database = require('better-sqlite3');
  db = new Database(dbPath);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
} catch (e) {
  console.error('Failed to initialize database:', e);
  process.exit(1);
}

export { db };
