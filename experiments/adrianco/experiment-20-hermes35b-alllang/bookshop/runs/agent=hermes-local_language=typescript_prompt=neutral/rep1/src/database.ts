import Database from 'better-sqlite3';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

// Minimal type definitions to avoid @types/better-sqlite3 version mismatch
type AnyStatement = {
  run: (...args: unknown[]) => unknown;
  get: (...args: unknown[]) => unknown;
  all: (...args: unknown[]) => unknown;
};

export interface DatabaseStatements {
  db: Database.Database;
  insertBook: AnyStatement;
  selectAllBooks: AnyStatement;
  selectBookById: AnyStatement;
  selectBooksByAuthor: AnyStatement;
  updateBook: AnyStatement;
  deleteBook: AnyStatement;
  countBooks: AnyStatement;
}

let dbStatements: DatabaseStatements | null = null;

export function createDatabase(dbPath: string): DatabaseStatements {
  const sql = new Database(dbPath);
  sql.pragma('journal_mode = WAL');
  sql.pragma('foreign_keys = ON');

  sql.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT UNIQUE
    )
  `);

  const stmts: DatabaseStatements = {
    db: sql,
    insertBook: sql.prepare(
      'INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)'
    ) as unknown as AnyStatement,
    selectAllBooks: sql.prepare('SELECT * FROM books') as unknown as AnyStatement,
    selectBookById: sql.prepare('SELECT * FROM books WHERE id = ?') as unknown as AnyStatement,
    selectBooksByAuthor: sql.prepare('SELECT * FROM books WHERE author = ?') as unknown as AnyStatement,
    updateBook: sql.prepare(
      'UPDATE books SET title = COALESCE(?, title), author = COALESCE(?, author), year = COALESCE(?, year), isbn = COALESCE(?, isbn) WHERE id = ?'
    ) as unknown as AnyStatement,
    deleteBook: sql.prepare('DELETE FROM books WHERE id = ?') as unknown as AnyStatement,
    countBooks: sql.prepare('SELECT COUNT(*) as count FROM books') as unknown as AnyStatement,
  };

  return stmts;
}

export function getDatabase(): DatabaseStatements {
  if (!dbStatements) {
    const filePath = path.join(__dirname, '..', 'books.db');
    dbStatements = createDatabase(filePath);
  }
  return dbStatements;
}

export function generateId(): string {
  return uuidv4();
}

export function closeDatabase(stmts: DatabaseStatements): void {
  stmts.db.close();
}
