import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type NewBook = Omit<Book, 'id'>;

/**
 * Create and initialize a SQLite-backed book store.
 * Pass ':memory:' (the default) for an ephemeral DB, useful for tests.
 */
export function createDb(filename = ':memory:'): Database.Database {
  const db = new Database(filename);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
  `);
  return db;
}

export function insertBook(db: Database.Database, book: NewBook): Book {
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const info = stmt.run(book.title, book.author, book.year, book.isbn);
  return getBook(db, Number(info.lastInsertRowid))!;
}

export function listBooks(db: Database.Database, author?: string): Book[] {
  if (author !== undefined) {
    return db
      .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
      .all(author) as Book[];
  }
  return db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
}

export function getBook(db: Database.Database, id: number): Book | undefined {
  return db.prepare('SELECT * FROM books WHERE id = ?').get(id) as
    | Book
    | undefined;
}

export function updateBook(
  db: Database.Database,
  id: number,
  book: NewBook
): Book | undefined {
  const info = db
    .prepare(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
    )
    .run(book.title, book.author, book.year, book.isbn, id);
  if (info.changes === 0) return undefined;
  return getBook(db, id);
}

export function deleteBook(db: Database.Database, id: number): boolean {
  const info = db.prepare('DELETE FROM books WHERE id = ?').run(id);
  return info.changes > 0;
}
