import Database from 'better-sqlite3';
import path from 'path';
import { randomUUID } from 'crypto';

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export class BookDatabase {
  private db: Database.Database;

  constructor(dbPathStr?: string) {
    const dbPath = dbPathStr || path.join('/tmp', 'books-test.db');
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('foreign_keys = true');
    this.initialize();
  }

  private initialize(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }

  create(title: string, author: string, year: number | null, isbn: string | null): Book {
    const id = randomUUID();
    const stmt = this.db.prepare(
      'INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)'
    );
    stmt.run(id, title, author, year, isbn);
    return this.findById(id) as Book;
  }

  findAll(author?: string): Book[] {
    if (author) {
      const stmt = this.db.prepare('SELECT * FROM books WHERE author = ?');
      return stmt.all(author) as Book[];
    }
    const stmt = this.db.prepare('SELECT * FROM books');
    return stmt.all() as Book[];
  }

  findById(id: string): Book | undefined {
    const stmt = this.db.prepare('SELECT * FROM books WHERE id = ?');
    return stmt.get(id) as Book | undefined;
  }

  update(id: string, updates: Partial<Pick<Book, 'title' | 'author' | 'year' | 'isbn'>>): Book | undefined {
    const existing = this.findById(id);
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

    if (setClauses.length > 0) {
      values.push(id);
      const stmt = this.db.prepare(
        `UPDATE books SET ${setClauses.join(', ')} WHERE id = ?`
      );
      stmt.run(...values);
    }

    return this.findById(id);
  }

  delete(id: string): Book | undefined {
    const existing = this.findById(id);
    if (!existing) return undefined;

    const stmt = this.db.prepare('DELETE FROM books WHERE id = ?');
    stmt.run(id);
    return existing;
  }

  close(): void {
    this.db.close();
  }
}
