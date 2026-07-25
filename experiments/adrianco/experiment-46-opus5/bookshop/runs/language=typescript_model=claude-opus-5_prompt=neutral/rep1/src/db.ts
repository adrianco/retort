import { DatabaseSync } from 'node:sqlite';
import type { Book, BookInput } from './types.js';

/** Thrown when a write would violate the unique constraint on `isbn`. */
export class DuplicateIsbnError extends Error {
  constructor(isbn: string) {
    super(`a book with isbn ${isbn} already exists`);
    this.name = 'DuplicateIsbnError';
  }
}

/** The shape rows come back as from SQLite before we narrow them to `Book`. */
interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function toBook(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
  };
}

/** `changes` is a number or a BigInt depending on the statement config. */
function changeCount(changes: number | bigint): number {
  return Number(changes);
}

function isUniqueViolation(err: unknown): boolean {
  return (
    err instanceof Error &&
    'code' in err &&
    (err as { code?: unknown }).code === 'ERR_SQLITE_ERROR' &&
    /UNIQUE constraint failed/i.test(err.message)
  );
}

/**
 * Data access for the book collection, backed by an embedded SQLite database.
 *
 * Pass `':memory:'` for an ephemeral database — that is what the tests use so
 * each one starts from a clean, isolated store.
 */
export class BookStore {
  private readonly db: DatabaseSync;

  constructor(filename: string) {
    this.db = new DatabaseSync(filename);
    this.db.exec('PRAGMA journal_mode = WAL');
    this.db.exec('PRAGMA foreign_keys = ON');
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        isbn   TEXT UNIQUE
      )
    `);
  }

  /** Lists books oldest-first by id, optionally filtered by author. */
  list(author?: string): Book[] {
    // Case-insensitive exact match. COLLATE NOCASE rather than LIKE so the
    // filter is always a literal — `%` matches nothing but a literal percent.
    const rows =
      author === undefined
        ? this.db.prepare('SELECT * FROM books ORDER BY id').all()
        : this.db
            .prepare('SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id')
            .all(author);
    return (rows as unknown as BookRow[]).map(toBook);
  }

  get(id: number): Book | null {
    const row = this.db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    return row === undefined ? null : toBook(row as unknown as BookRow);
  }

  create(input: BookInput): Book {
    try {
      const result = this.db
        .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
        .run(input.title, input.author, input.year, input.isbn);
      return { id: Number(result.lastInsertRowid), ...input };
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn !== null) {
        throw new DuplicateIsbnError(input.isbn);
      }
      throw err;
    }
  }

  /** Replaces a book wholesale. Returns null when no book has that id. */
  update(id: number, input: BookInput): Book | null {
    try {
      const result = this.db
        .prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
        .run(input.title, input.author, input.year, input.isbn, id);
      return changeCount(result.changes) === 0 ? null : { id, ...input };
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn !== null) {
        throw new DuplicateIsbnError(input.isbn);
      }
      throw err;
    }
  }

  /** Returns true when a row was removed, false when the id was unknown. */
  delete(id: number): boolean {
    const result = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return changeCount(result.changes) > 0;
  }

  /** Round-trips a trivial query so the health check reflects real DB state. */
  ping(): void {
    this.db.prepare('SELECT 1').get();
  }

  close(): void {
    this.db.close();
  }
}
