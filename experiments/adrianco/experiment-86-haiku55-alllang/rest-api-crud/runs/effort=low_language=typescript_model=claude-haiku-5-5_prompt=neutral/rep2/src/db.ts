import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export type Database = DatabaseSync;

export function openDatabase(path: string = ':memory:'): Database {
  const db = new DatabaseSync(path);
  db.exec('PRAGMA foreign_keys = ON;');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
  `);
  return db;
}

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export class BookRepository {
  constructor(private readonly db: Database) {}

  create(input: BookInput): Book {
    const result = this.db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null);
    return this.findById(Number(result.lastInsertRowid))!;
  }

  findById(id: number): Book | undefined {
    const row = this.db
      .prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?')
      .get(id) as BookRow | undefined;
    return row;
  }

  list(author?: string): Book[] {
    if (author === undefined) {
      return this.db
        .prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id')
        .all() as unknown as BookRow[];
    }
    return this.db
      .prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id')
      .all(author) as unknown as BookRow[];
  }

  update(id: number, input: BookInput): Book | undefined {
    const result = this.db
      .prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
    if (result.changes === 0) return undefined;
    return this.findById(id);
  }

  delete(id: number): boolean {
    const result = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return result.changes > 0;
  }
}
