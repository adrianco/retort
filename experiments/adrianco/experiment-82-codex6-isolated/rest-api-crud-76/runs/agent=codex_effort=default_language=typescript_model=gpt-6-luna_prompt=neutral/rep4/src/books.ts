import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type BookInput = Pick<Book, 'title' | 'author'> & Partial<Pick<Book, 'year' | 'isbn'>>;

export class BookStore {
  private readonly db: DatabaseSync;

  constructor(filename = process.env.DATABASE_PATH ?? 'books.db') {
    this.db = new DatabaseSync(filename);
    this.db.exec(`CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )`);
  }

  list(author?: string): Book[] {
    const rows = author
      ? this.db.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id').all(author)
      : this.db.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id').all();
    return rows as unknown as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare('SELECT id, title, author, year, isbn FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
  }

  create(input: BookInput): Book {
    const result = this.db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(input.title.trim(), input.author.trim(), input.year ?? null, input.isbn ?? null);
    return this.get(Number(result.lastInsertRowid))!;
  }

  update(id: number, input: BookInput): Book | undefined {
    const result = this.db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?')
      .run(input.title.trim(), input.author.trim(), input.year ?? null, input.isbn ?? null, id);
    return Number(result.changes) ? this.get(id) : undefined;
  }

  delete(id: number): boolean {
    return Number(this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes) > 0;
  }

  close(): void { this.db.close(); }
}
