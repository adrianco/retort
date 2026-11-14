import Database from 'better-sqlite3';
import { Book } from './types';

const db = Database(':memory:');

export function initializeDatabase(): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER NOT NULL,
      isbn TEXT NOT NULL UNIQUE
    )
  `);
}

export function getAllBooks(author?: string): Book[] {
  if (author) {
    return db.prepare('SELECT * FROM books WHERE author = ?').all(author) as Book[];
  }
  return db.prepare('SELECT * FROM books').all() as Book[];
}

export function getBookById(id: number): Book | undefined {
  return db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
}

export function createBook(title: string, author: string, year: number, isbn: string): Book {
  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year, isbn);
  return { id: Number(result.lastInsertRowid), title, author, year, isbn };
}

export function updateBook(id: number, updates: { title?: string; author?: string; year?: number; isbn?: string }): Book | undefined {
  const book = getBookById(id);
  if (!book) return undefined;

  const setClauses: string[] = [];
  const values: unknown[] = [];

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

  if (setClauses.length === 0) return book;

  db.prepare(`UPDATE books SET ${setClauses.join(', ')} WHERE id = ?`).run(...values, id);
  return getBookById(id)!;
}

export function deleteBook(id: number): boolean {
  const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  return result.changes > 0;
}

export function clearAllBooks(): void {
  db.prepare('DELETE FROM books').run();
}
