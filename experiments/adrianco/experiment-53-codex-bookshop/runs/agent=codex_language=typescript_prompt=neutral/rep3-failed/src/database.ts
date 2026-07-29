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

type Row = { id: number; title: string; author: string; year: number | null; isbn: string | null };

export class BookRepository {
  private readonly db: DatabaseSync;

  constructor(db: DatabaseSync) {
    this.db = db;
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

  list(author?: string): Book[] {
    const statement = author
      ? this.db.prepare('SELECT id, title, author, year, isbn FROM books WHERE author LIKE ? COLLATE NOCASE ORDER BY id')
      : this.db.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id');
    return (author ? statement.all(`%${author}%`) : statement.all()).map((row) => this.toBook(row as Row));
  }

  find(id: number): Book | null {
    const row = this.db.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?').get(id) as Row | undefined;
    return row ? this.toBook(row) : null;
  }

  create(input: BookInput): Book {
    const result = this.db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)').run(input.title, input.author, input.year ?? null, input.isbn ?? null);
    return this.find(Number(result.lastInsertRowid))!;
  }

  update(id: number, input: BookInput): Book | null {
    const result = this.db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
    return Number(result.changes) ? this.find(id) : null;
  }

  delete(id: number): boolean {
    return Number(this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes) > 0;
  }

  close(): void { this.db.close(); }

  private toBook(row: Row): Book { return { id: row.id, title: row.title, author: row.author, year: row.year, isbn: row.isbn }; }
}
