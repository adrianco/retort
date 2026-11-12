import initSqlJs, { Database } from 'sql.js';
import { Book } from './types';

let db: Database | null = null;
let initPromise: Promise<void> | null = null;

async function getDb(): Promise<Database> {
  if (db) return db;
  if (!initPromise) {
    initPromise = (async () => {
      const SQL = await initSqlJs();
      db = new SQL.Database();
      db.run(`
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER NOT NULL,
          isbn TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
      `);
    })();
  }
  await initPromise;
  return db!;
}

export async function getAllBooks(author?: string): Promise<Book[]> {
  const database = await getDb();
  let results: any[];
  if (author) {
    results = database.prepare('SELECT * FROM books WHERE author = ?').all({ 1: author });
  } else {
    results = database.prepare('SELECT * FROM books ORDER BY id DESC').all();
  }
  return results.map(row => ({
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    created_at: row.created_at,
    updated_at: row.updated_at,
  }));
}

export async function getBookById(id: number): Promise<Book | undefined> {
  const database = await getDb();
  const row = database.prepare('SELECT * FROM books WHERE id = ?').get({ 1: id });
  if (!row) return undefined;
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

export async function createBook(title: string, author: string, year: number, isbn: string): Promise<Book> {
  const database = await getDb();
  database.run('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', [title, author, year, isbn]);
  const id = database.getLastInsertRowid() as number;
  return (await getBookById(id))!;
}

export async function updateBook(id: number, title?: string, author?: string, year?: number, isbn?: string): Promise<Book | undefined> {
  const existing = await getBookById(id);
  if (!existing) return undefined;

  const updates: string[] = [];
  const values: any[] = [];
  let param = 1;

  if (title !== undefined) {
    updates.push(`title = ?`);
    values.push(title);
  }
  if (author !== undefined) {
    updates.push(`author = ?`);
    values.push(author);
  }
  if (year !== undefined) {
    updates.push(`year = ?`);
    values.push(year);
  }
  if (isbn !== undefined) {
    updates.push(`isbn = ?`);
    values.push(isbn);
  }

  updates.push("updated_at = datetime('now')");
  values.push(id);

  const placeholders = values.map(() => '?').join(', ');
  database.run(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`, [...values, id]);
  return await getBookById(id);
}

export async function deleteBook(id: number): Promise<boolean> {
  const database = await getDb();
  const result = database.run('DELETE FROM books WHERE id = ?', [id]);
  return result === 1;
}
