import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(__dirname, '..', 'data', 'books.db');

// Ensure data directory exists
import fs from 'fs';
const dataDir = path.join(__dirname, '..', 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new Database(DB_PATH);

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

export type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

export function getAllBooks(author?: string): Book[] {
  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    return stmt.all(author) as Book[];
  }
  const stmt = db.prepare('SELECT * FROM books');
  return stmt.all() as Book[];
}

export function getBookById(id: number): Book | undefined {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  return stmt.get(id) as Book | undefined;
}

export function createBook(title: string, author: string, year?: number, isbn?: string): Book {
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const result = stmt.run(title, author, year ?? null, isbn ?? null);
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
  return book;
}

export function updateBook(id: number, updates: Partial<Pick<Book, 'title' | 'author' | 'year' | 'isbn'>>): Book | undefined {
  const existing = getBookById(id);
  if (!existing) return undefined;

  const setClauses: string[] = [];
  const values: (string | number | null)[] = [];

  if (updates.title !== undefined) {
    setClauses.push('title = ?');
    values.push(updates.title);
  }
  if (updates.author !== undefined) {
    setClauses.push('author = ?');
    values.push(updates.author);
  }
  if (updates.year !== undefined) {
    setClauses.push('year = ?');
    values.push(updates.year);
  }
  if (updates.isbn !== undefined) {
    setClauses.push('isbn = ?');
    values.push(updates.isbn);
  }

  if (setClauses.length === 0) {
    return existing;
  }

  values.push(id);
  const stmt = db.prepare(`UPDATE books SET ${setClauses.join(', ')} WHERE id = ?`);
  stmt.run(...values);

  return getBookById(id);
}

export function deleteBook(id: number): boolean {
  const existing = getBookById(id);
  if (!existing) return false;

  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}

export function closeDatabase(): void {
  db.close();
}
