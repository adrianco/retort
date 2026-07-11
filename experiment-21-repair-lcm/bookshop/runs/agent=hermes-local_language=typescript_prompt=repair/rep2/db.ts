import Database from "better-sqlite3";
import type { Database as DatabaseType } from "better-sqlite3";

let dbInstance: DatabaseType | null = null;

function getDb(): DatabaseType {
  if (!dbInstance) {
    dbInstance = new Database(":memory:");
    dbInstance.pragma("journal_mode = WAL");

    dbInstance.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }
  return dbInstance;
}

export function initializeDatabase(dbPath?: string) {
  if (dbInstance) {
    dbInstance.close();
  }
  dbInstance = new Database(dbPath || ":memory:");
  dbInstance.pragma("journal_mode = WAL");

  dbInstance.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
}

export function getAllBooks(authorFilter?: string) {
  const db = getDb();
  if (authorFilter) {
    return db
      .prepare("SELECT * FROM books WHERE author = ?")
      .all(authorFilter) as Book[];
  }
  return db.prepare("SELECT * FROM books").all() as Book[];
}

export function getBookById(id: number) {
  const db = getDb();
  return db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;
}

export function createBook(title: string, author: string, year?: number, isbn?: string) {
  const db = getDb();
  const stmt = db.prepare(
    "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
  );
  const result = stmt.run(title, author, year ?? null, isbn ?? null);
  return db.prepare("SELECT * FROM books WHERE id = ?").get(result.lastInsertRowid) as Book;
}

export function updateBook(
  id: number,
  title?: string,
  author?: string,
  year?: number,
  isbn?: string
) {
  const db = getDb();
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;
  if (!existing) return undefined;

  const newTitle = title ?? existing.title;
  const newAuthor = author ?? existing.author;
  const newYear = year ?? existing.year;
  const newIsbn = isbn ?? existing.isbn;

  db.prepare(
    "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
  ).run(newTitle, newAuthor, newYear, newIsbn, id);

  return db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book;
}

export function deleteBook(id: number) {
  const db = getDb();
  const existing = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | undefined;
  if (!existing) return false;

  db.prepare("DELETE FROM books WHERE id = ?").run(id);
  return true;
}

export function closeDatabase() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

export type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};
