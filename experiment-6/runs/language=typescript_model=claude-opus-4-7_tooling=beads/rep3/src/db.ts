import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface NewBook {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
}

export function createDatabase(filename: string = ':memory:'): Database.Database {
  const db = new Database(filename);
  db.pragma('journal_mode = WAL');
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
  constructor(private db: Database.Database) {}

  create(book: NewBook): Book {
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const info = stmt.run(
      book.title,
      book.author,
      book.year ?? null,
      book.isbn ?? null
    );
    return this.getById(Number(info.lastInsertRowid))!;
  }

  list(authorFilter?: string): Book[] {
    if (authorFilter) {
      return this.db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(authorFilter) as Book[];
    }
    return this.db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
  }

  getById(id: number): Book | undefined {
    return this.db
      .prepare('SELECT * FROM books WHERE id = ?')
      .get(id) as Book | undefined;
  }

  update(id: number, book: NewBook): Book | undefined {
    const existing = this.getById(id);
    if (!existing) return undefined;
    this.db
      .prepare(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
      )
      .run(book.title, book.author, book.year ?? null, book.isbn ?? null, id);
    return this.getById(id);
  }

  delete(id: number): boolean {
    const info = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return info.changes > 0;
  }
}
