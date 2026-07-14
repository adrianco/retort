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

/**
 * Creates a database connection and ensures the schema exists.
 * Pass ':memory:' (the default) for an ephemeral in-memory DB,
 * or a file path to persist data on disk.
 */
export function createDb(location = ':memory:'): DatabaseSync {
  const db = new DatabaseSync(location);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
  `);
  return db;
}

export class BookRepository {
  constructor(private readonly db: DatabaseSync) {}

  create(input: BookInput): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.getById(Number(result.lastInsertRowid))!;
  }

  list(author?: string): Book[] {
    if (author) {
      const stmt = this.db.prepare(
        'SELECT * FROM books WHERE author = ? ORDER BY id'
      );
      return stmt.all(author) as unknown as Book[];
    }
    const stmt = this.db.prepare('SELECT * FROM books ORDER BY id');
    return stmt.all() as unknown as Book[];
  }

  getById(id: number): Book | undefined {
    const stmt = this.db.prepare('SELECT * FROM books WHERE id = ?');
    return stmt.get(id) as unknown as Book | undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const existing = this.getById(id);
    if (!existing) return undefined;
    const stmt = this.db.prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    );
    stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null,
      id
    );
    return this.getById(id);
  }

  delete(id: number): boolean {
    const stmt = this.db.prepare('DELETE FROM books WHERE id = ?');
    const result = stmt.run(id);
    return result.changes > 0;
  }
}
