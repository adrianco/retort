import Database from 'better-sqlite3';

// Import the Database type from the type declarations
type DB = Database.Database;

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

let appDb: DB | null = null;

export function createDb(path: string): DB {
  const db = new Database(path);
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
  return db as unknown as DB;
}

export function getAppDb(): DB | null {
  return appDb;
}

export function setAppDb(db: DB): void {
  appDb = db;
}

export function clearAll(db: DB): void {
  db.exec('DELETE FROM books');
}

export function createBook(
  db: DB,
  title: string,
  author: string,
  year?: number,
  isbn?: string
): Book {
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const info = stmt.run(title, author, year ?? null, isbn ?? null);
  const id = Number(info.lastInsertRowid);
  return { id, title, author, year: year ?? 0, isbn: isbn ?? '' };
}

export function getAllBooks(db: DB, author?: string): Book[] {
  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ?');
    return stmt.all(author) as Book[];
  }
  const stmt = db.prepare('SELECT * FROM books');
  return stmt.all() as Book[];
}

export function getBook(db: DB, id: number): Book | null {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const row = stmt.get(id) as Book | undefined;
  return row ?? null;
}

export function updateBook(
  db: DB,
  id: number,
  title: string,
  author: string,
  year?: number,
  isbn?: string
): Book | null {
  const existing = getBook(db, id);
  if (!existing) return null;
  const stmt = db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
  );
  stmt.run(title, author, year ?? null, isbn ?? null, id);
  return { id, title, author, year: year ?? 0, isbn: isbn ?? '' };
}

export function deleteBook(db: DB, id: number): Book | null {
  const existing = getBook(db, id);
  if (!existing) return null;
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  stmt.run(id);
  return existing;
}

export function COUNT_ALL(db: DB): number {
  const stmt = db.prepare('SELECT COUNT(*) as count FROM books');
  const result = stmt.get() as { count: number };
  return result.count;
}

export function COUNT_BY_AUTHOR(db: DB, author: string): number {
  const stmt = db.prepare('SELECT COUNT(*) as count FROM books WHERE author = ?');
  const result = stmt.get(author) as { count: number };
  return result.count;
}

export function shutdownDb(): void {
  if (appDb) {
    (appDb as any).close();
    appDb = null;
  }
}
