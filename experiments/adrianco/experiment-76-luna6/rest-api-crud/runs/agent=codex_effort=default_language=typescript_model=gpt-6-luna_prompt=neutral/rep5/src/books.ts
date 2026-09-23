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

export class BookStore {
  private readonly db: DatabaseSync;

  constructor(databasePath = process.env.DATABASE_PATH ?? './books.sqlite') {
    this.db = new DatabaseSync(databasePath);
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
    const rows = author === undefined
      ? this.db.prepare('SELECT id, title, author, year, isbn FROM books ORDER BY id').all()
      : this.db.prepare('SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id').all(author);
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
    return Number(result.changes) === 0 ? undefined : this.get(id);
  }

  delete(id: number): boolean {
    return Number(this.db.prepare('DELETE FROM books WHERE id = ?').run(id).changes) > 0;
  }

  close(): void { this.db.close(); }
}

export function validateBook(value: unknown): { input?: BookInput; error?: string } {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return { error: 'Request body must be a JSON object' };
  const body = value as Record<string, unknown>;
  if (typeof body.title !== 'string' || !body.title.trim()) return { error: 'title is required and must be a non-empty string' };
  if (typeof body.author !== 'string' || !body.author.trim()) return { error: 'author is required and must be a non-empty string' };
  if (body.year !== undefined && body.year !== null && (!Number.isInteger(body.year) || (body.year as number) < 0)) {
    return { error: 'year must be a non-negative integer or null' };
  }
  if (body.isbn !== undefined && body.isbn !== null && typeof body.isbn !== 'string') return { error: 'isbn must be a string or null' };
  return { input: { title: body.title, author: body.author, year: body.year as number | null | undefined, isbn: body.isbn as string | null | undefined } };
}
