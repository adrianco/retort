import { DatabaseSync } from 'node:sqlite';

export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}
export interface Book extends BookInput { id: number }

export class BookStore {
  private readonly db: DatabaseSync;

  constructor(path = ':memory:') {
    this.db = new DatabaseSync(path);
    this.db.exec(`
      PRAGMA busy_timeout = 5000;
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL CHECK(length(trim(title)) > 0),
        author TEXT NOT NULL CHECK(length(trim(author)) > 0),
        year INTEGER,
        isbn TEXT
      );
    `);
  }

  list(author?: string): Book[] {
    return (author === undefined
      ? this.db.prepare('SELECT * FROM books ORDER BY id').all()
      : this.db.prepare('SELECT * FROM books WHERE author = ? ORDER BY id').all(author)) as unknown as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
  }

  create(book: BookInput): Book {
    const result = this.db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(book.title, book.author, book.year, book.isbn);
    return this.get(Number(result.lastInsertRowid))!;
  }

  update(id: number, book: BookInput): Book | undefined {
    const result = this.db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(book.title, book.author, book.year, book.isbn, id);
    return result.changes ? this.get(id) : undefined;
  }

  delete(id: number): boolean {
    return this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes > 0;
  }

  healthy(): boolean { return this.db.prepare('SELECT 1').get() !== undefined; }
  close(): void { this.db.close(); }
}
