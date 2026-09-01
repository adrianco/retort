import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

let db: Database.Database | null = null;
let currentDbPath: string = path.join(__dirname, '..', 'books.db');

function createDb(dbPath: string): Database.Database {
  const database = new Database(dbPath);
  database.pragma('journal_mode = WAL');
  database.pragma('foreign_keys = true');
  database.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )
  `);
  return database;
}

function getDb(): Database.Database {
  if (!db) {
    db = createDb(currentDbPath);
  }
  return db;
}

export function getAllBooks(author?: string): Book[] {
  const db = getDb();
  if (author) {
    return db.prepare('SELECT * FROM books WHERE author = ?').all(author) as Book[];
  }
  return db.prepare('SELECT * FROM books').all() as Book[];
}

export function getBookById(id: number): Book | undefined {
  const db = getDb();
  return db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
}

export function createBook(title: string, author: string, year?: number, isbn?: string): Book {
  const db = getDb();
  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year ?? null, isbn ?? null);
  return { id: result.lastInsertRowid as number, title, author, year: year ?? null, isbn: isbn ?? null };
}

export function updateBook(id: number, title?: string, author?: string, year?: number, isbn?: string): Book | undefined {
  const db = getDb();
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!book) return undefined;

  const newTitle = title ?? book.title;
  const newAuthor = author ?? book.author;
  const newYear = year ?? book.year;
  const newIsbn = isbn ?? book.isbn;

  db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
    .run(newTitle, newAuthor, newYear, newIsbn, id);

  return db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
}

export function deleteBook(id: number): boolean {
  const db = getDb();
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
  if (!book) return false;
  db.prepare('DELETE FROM books WHERE id = ?').run(id);
  return true;
}

export function closeDb(): void {
  if (db) {
    try { db.close(); } catch { /* ignore */ }
    db = null;
  }
}

export function resetDb(): void {
  closeDb();
  [currentDbPath, currentDbPath + '-wal', currentDbPath + '-shm'].forEach(p => {
    if (fs.existsSync(p)) {
      try { fs.unlinkSync(p); } catch { /* ignore */ }
    }
  });
}
