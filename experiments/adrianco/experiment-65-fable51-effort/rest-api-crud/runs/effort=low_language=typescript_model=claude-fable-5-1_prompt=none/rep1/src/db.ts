import type { DatabaseSync as DatabaseSyncType } from 'node:sqlite';

// Loaded via getBuiltinModule so bundlers/test runners that don't know
// about node:sqlite (e.g. vite) leave the import alone.
const { DatabaseSync } = process.getBuiltinModule('node:sqlite') as typeof import('node:sqlite');

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

export class BookRepository {
  private db: DatabaseSyncType;

  constructor(path: string = ':memory:') {
    this.db = new DatabaseSync(path);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }

  create(input: BookInput): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    );
    const result = stmt.run(input.title, input.author, input.year ?? null, input.isbn ?? null);
    return this.get(Number(result.lastInsertRowid))!;
  }

  list(author?: string): Book[] {
    if (author !== undefined) {
      return this.db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as unknown as Book[];
    }
    return this.db.prepare('SELECT * FROM books ORDER BY id').all() as unknown as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as
      | Book
      | undefined;
  }

  update(id: number, input: BookInput): Book | undefined {
    const result = this.db
      .prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
    if (result.changes === 0) return undefined;
    return this.get(id);
  }

  delete(id: number): boolean {
    return this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
