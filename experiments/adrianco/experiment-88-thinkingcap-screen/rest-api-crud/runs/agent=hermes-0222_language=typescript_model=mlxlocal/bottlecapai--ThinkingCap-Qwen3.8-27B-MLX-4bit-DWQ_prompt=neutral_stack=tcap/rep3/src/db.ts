import { DatabaseSync } from 'node:sqlite';

/** A book as stored in the database and returned by the API. */
export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** Fields accepted when creating or updating a book. */
export interface BookFields {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/**
 * Open (or create) the SQLite database at `path` and ensure the schema
 * exists. Pass ':memory:' for an in-memory database (used by tests).
 */
export function openDb(path: string): DatabaseSync {
  const db = new DatabaseSync(path);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_books_author ON books (author);
  `);
  return db;
}

export function closeDb(db: DatabaseSync): void {
  db.close();
}

function rowToBook(row: Record<string, unknown>): Book {
  return {
    id: Number(row.id),
    title: String(row.title),
    author: String(row.author),
    year: row.year === null ? null : Number(row.year),
    isbn: row.isbn === null ? null : String(row.isbn),
  };
}

/** List all books, optionally filtered by author (case-insensitive exact match). */
export function listBooks(db: DatabaseSync, author?: string): Book[] {
  if (author !== undefined) {
    const rows = db
      .prepare('SELECT * FROM books WHERE lower(author) = lower(?) ORDER BY id')
      .all(author) as Record<string, unknown>[];
    return rows.map(rowToBook);
  }
  const rows = db
    .prepare('SELECT * FROM books ORDER BY id')
    .all() as Record<string, unknown>[];
  return rows.map(rowToBook);
}

/** Get a single book by id, or null if it does not exist. */
export function getBook(db: DatabaseSync, id: number): Book | null {
  const row = db
    .prepare('SELECT * FROM books WHERE id = ?')
    .get(id) as Record<string, unknown> | undefined;
  return row ? rowToBook(row) : null;
}

/** Insert a new book and return it (with its generated id). */
export function createBook(db: DatabaseSync, fields: BookFields): Book {
  const result = db
    .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
    .run(fields.title, fields.author, fields.year ?? null, fields.isbn ?? null);
  const book = getBook(db, Number(result.lastInsertRowid));
  if (!book) throw new Error('Failed to create book');
  return book;
}

/**
 * Update the provided fields of a book. `patch` may contain any subset of
 * title, author, year, isbn; explicit nulls clear year/isbn.
 * Returns the updated book, or null if no book with that id exists.
 */
export function updateBook(
  db: DatabaseSync,
  id: number,
  patch: Partial<BookFields>,
): Book | null {
  const sets: string[] = [];
  const values: (string | number | null)[] = [];
  if (patch.title !== undefined) {
    sets.push('title = ?');
    values.push(patch.title);
  }
  if (patch.author !== undefined) {
    sets.push('author = ?');
    values.push(patch.author);
  }
  if (patch.year !== undefined) {
    sets.push('year = ?');
    values.push(patch.year);
  }
  if (patch.isbn !== undefined) {
    sets.push('isbn = ?');
    values.push(patch.isbn);
  }
  if (sets.length === 0) return getBook(db, id);

  values.push(id);
  const result = db
    .prepare(`UPDATE books SET ${sets.join(', ')} WHERE id = ?`)
    .run(...values);
  if (Number(result.changes) === 0) return null;
  return getBook(db, id);
}

/** Delete a book by id. Returns true if a row was deleted. */
export function deleteBook(db: DatabaseSync, id: number): boolean {
  const result = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  return Number(result.changes) > 0;
}
