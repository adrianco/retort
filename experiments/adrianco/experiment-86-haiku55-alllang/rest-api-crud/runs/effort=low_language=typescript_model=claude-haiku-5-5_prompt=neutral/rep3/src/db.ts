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

export class BookRepository {
  private readonly db: DatabaseSync;

  constructor(path: string = ':memory:') {
    this.db = new DatabaseSync(path);
    this.db.exec('PRAGMA journal_mode = WAL;');
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
    const result = this.db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title, input.author, input.year ?? null, input.isbn ?? null);
    return this.findById(Number(result.lastInsertRowid))!;
  }

  findById(id: number): Book | undefined {
    const row = this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as BookRow | undefined;
    return row ? toBook(row) : undefined;
  }

  findAll(author?: string): Book[] {
    const rows = author === undefined
      ? this.db.prepare('SELECT * FROM books ORDER BY id').all()
      : this.db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author);
    return (rows as unknown as BookRow[]).map(toBook);
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

  ping(): boolean {
    this.db.prepare('SELECT 1').get();
    return true;
  }

  close(): void {
    this.db.close();
  }
}

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

function toBook(row: BookRow): Book {
  return { id: row.id, title: row.title, author: row.author, year: row.year, isbn: row.isbn };
}
