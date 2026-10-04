import { randomUUID } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';

export interface Book {
  id: string;
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

export class BookStore {
  constructor(private readonly db: DatabaseSync) {
    db.exec(`CREATE TABLE IF NOT EXISTS books (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
      year INTEGER, isbn TEXT
    )`);
  }

  list(author?: string): Book[] {
    const rows = author === undefined
      ? this.db.prepare('SELECT * FROM books ORDER BY rowid').all()
      : this.db.prepare('SELECT * FROM books WHERE author = ? ORDER BY rowid').all(author);
    return rows as unknown as Book[];
  }

  get(id: string): Book | undefined {
    return this.db.prepare('SELECT * FROM books WHERE id = ?').get(id) as unknown as Book | undefined;
  }

  create(input: BookInput): Book {
    const book: Book = { id: randomUUID(), title: input.title.trim(), author: input.author.trim(), year: input.year ?? null, isbn: input.isbn ?? null };
    this.db.prepare('INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)').run(book.id, book.title, book.author, book.year, book.isbn);
    return book;
  }

  update(id: string, input: BookInput): Book | undefined {
    const result = this.db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(input.title.trim(), input.author.trim(), input.year ?? null, input.isbn ?? null, id);
    return Number(result.changes) === 0 ? undefined : this.get(id);
  }

  delete(id: string): boolean {
    return Number(this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes) > 0;
  }
}
