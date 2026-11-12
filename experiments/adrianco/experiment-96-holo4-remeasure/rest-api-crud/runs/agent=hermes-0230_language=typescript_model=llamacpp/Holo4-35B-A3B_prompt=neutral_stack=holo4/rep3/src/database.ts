import initSqlJs, { Database } from 'sql.js';
import path from 'path';
import { Book } from './types';

let db: Database | null = null;

const DB_PATH = path.join(__dirname, '..', 'books.db');

async function init() {
  const SQL = await initSqlJs();
  let data: Uint8Array | undefined;
  try {
    const fs = require('fs');
    data = fs.readFileSync(DB_PATH);
  } catch {
    // No existing database, start fresh
  }
  db = data ? new SQL.Database(data) : new SQL.Database();
  db.run(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
}

function save() {
  if (!db) return;
  const fs = require('fs');
  const data = db.export();
  fs.writeFileSync(DB_PATH, Buffer.from(data));
}

function rowToBook(row: Record<string, any>): Book {
  return {
    id: Number(row.id),
    title: row.title,
    author: row.author,
    year: Number(row.year),
    isbn: row.isbn,
  };
}

function getBook(id: number): Book | undefined {
  if (!db) return undefined;
  const result = db.exec('SELECT * FROM books WHERE id = ?', [id]);
  if (!result[0] || !result[0].values.length) {
    return undefined;
  }
  const columns = result[0].columns;
  const row = result[0].values[0];
  return rowToBook(Object.fromEntries(columns.map((col, i) => [col, row[i]])));
}

function getBooks(author?: string): Book[] {
  if (!db) return [];
  const sql = author ? 'SELECT * FROM books WHERE author = ?' : 'SELECT * FROM books';
  const result = db.exec(sql, author ? [author] : undefined);
  if (!result[0] || !result[0].values.length) {
    return [];
  }
  const columns = result[0].columns;
  return result[0].values.map((row) =>
    rowToBook(Object.fromEntries(columns.map((col, i) => [col, row[i]])))
  );
}

export { db, init, save, getBook, getBooks };
