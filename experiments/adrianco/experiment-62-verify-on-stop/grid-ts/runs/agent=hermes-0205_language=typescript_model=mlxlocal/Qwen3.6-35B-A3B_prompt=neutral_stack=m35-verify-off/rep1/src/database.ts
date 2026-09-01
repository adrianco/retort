import Database from 'better-sqlite3';
import path from 'path';

let dbInstance: Database.Database | null = null;

function getDb(): Database.Database {
  if (!dbInstance) {
    const dbPath = process.env.DB_PATH || path.join(__dirname, '..', 'books.db');
    dbInstance = new Database(dbPath);
    dbInstance.pragma('journal_mode = WAL');
    dbInstance.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT UNIQUE
      )
    `);
  }
  return dbInstance;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export function resetDatabase(): void {
  if (dbInstance) {
    try {
      dbInstance.close();
    } catch {
      // ignore
    }
    dbInstance = null;
  }
}

export function getAllBooks(author?: string): Book[] {
  const db = getDb();
  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    return stmt.all(author) as Book[];
  }
  const stmt = db.prepare('SELECT * FROM books');
  return stmt.all() as Book[];
}

export function getBookById(id: number): Book | undefined {
  const db = getDb();
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  return stmt.get(id) as Book | undefined;
}

export function createBook(
  title: string,
  author: string,
  year: number | null,
  isbn: string | null
): Book {
  const db = getDb();
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const result = stmt.run(title, author, year, isbn);
  return {
    id: result.lastInsertRowid as number,
    title,
    author,
    year,
    isbn,
  };
}

export function updateBook(
  id: number,
  title: string | undefined,
  author: string | undefined,
  year: number | null | undefined,
  isbn: string | null | undefined
): Book | undefined {
  const existing = getBookById(id);
  if (!existing) return undefined;

  const newTitle = title ?? existing.title;
  const newAuthor = author ?? existing.author;
  const newYear = year ?? existing.year;
  const newIsbn = isbn ?? existing.isbn;

  const db = getDb();
  const stmt = db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  );
  stmt.run(newTitle, newAuthor, newYear, newIsbn, id);

  return getBookById(id);
}

export function deleteBook(id: number): boolean {
  const db = getDb();
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}

export function closeDb(): void {
  resetDatabase();
}
