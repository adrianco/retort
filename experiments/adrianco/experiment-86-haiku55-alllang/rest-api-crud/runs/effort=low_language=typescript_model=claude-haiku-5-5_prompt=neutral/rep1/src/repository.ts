import { DatabaseSync } from 'node:sqlite';
import type { Book, BookInput } from './book';

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

const toBook = (r: BookRow): Book => ({
  id: r.id,
  title: r.title,
  author: r.author,
  year: r.year,
  isbn: r.isbn,
});

/** Data access for books, backed by an embedded SQLite database. */
export class BookRepository {
  private readonly db: DatabaseSync;

  constructor(filename: string = ':memory:') {
    this.db = new DatabaseSync(filename);
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT
      );
      CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
    `);
  }

  create(input: BookInput): Book {
    const result = this.db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null);
    return this.findById(Number(result.lastInsertRowid)) as Book;
  }

  findById(id: number): Book | undefined {
    const row = this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as BookRow | undefined;
    return row ? toBook(row) : undefined;
  }

  /** Lists books ordered by id; optionally filters by exact author match (case-insensitive). */
  findAll(filter: { author?: string } = {}): Book[] {
    const rows = filter.author !== undefined
      ? this.db.prepare('SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id').all(filter.author)
      : this.db.prepare('SELECT * FROM books ORDER BY id').all();
    return (rows as unknown as BookRow[]).map(toBook);
  }

  /** Replaces the mutable fields of an existing book. Returns undefined if no such book. */
  update(id: number, input: Partial<BookInput>): Book | undefined {
    const current = this.findById(id);
    if (!current) return undefined;
    const merged = {
      title: input.title ?? current.title,
      author: input.author ?? current.author,
      year: input.year !== undefined ? input.year : current.year,
      isbn: input.isbn !== undefined ? input.isbn : current.isbn,
    };
    this.db
      .prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(merged.title, merged.author, merged.year, merged.isbn, id);
    return this.findById(id);
  }

  delete(id: number): boolean {
    const result = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return Number(result.changes) > 0;
  }

  ping(): boolean {
    this.db.prepare('SELECT 1').get();
    return true;
  }

  close(): void {
    this.db.close();
  }
}
