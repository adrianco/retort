import type { DatabaseSync } from "node:sqlite";
import type { CreateBookInput, UpdateBookInput } from "./validation.js";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  createdAt: string;
  updatedAt: string;
}

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export class DuplicateIsbnError extends Error {
  constructor(isbn: string) {
    super(`A book with isbn ${isbn} already exists`);
    this.name = "DuplicateIsbnError";
  }
}

function toBook(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function isUniqueViolation(err: unknown): boolean {
  return (
    err instanceof Error &&
    /UNIQUE constraint failed/i.test(err.message)
  );
}

export class BookRepository {
  constructor(private readonly db: DatabaseSync) {}

  create(input: CreateBookInput): Book {
    try {
      const result = this.db
        .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
        .run(input.title, input.author, input.year ?? null, input.isbn ?? null);
      return this.findById(Number(result.lastInsertRowid))!;
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn) throw new DuplicateIsbnError(input.isbn);
      throw err;
    }
  }

  findAll(filter: { author?: string } = {}): Book[] {
    if (filter.author !== undefined) {
      const rows = this.db
        .prepare("SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id")
        .all(filter.author) as unknown as BookRow[];
      return rows.map(toBook);
    }
    const rows = this.db.prepare("SELECT * FROM books ORDER BY id").all() as unknown as BookRow[];
    return rows.map(toBook);
  }

  findById(id: number): Book | undefined {
    const row = this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as unknown as BookRow | undefined;
    return row ? toBook(row) : undefined;
  }

  update(id: number, input: UpdateBookInput): Book | undefined {
    try {
      const result = this.db
        .prepare(
          `UPDATE books
             SET title = ?, author = ?, year = ?, isbn = ?,
                 updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
           WHERE id = ?`,
        )
        .run(input.title, input.author, input.year ?? null, input.isbn ?? null, id);
      if (result.changes === 0) return undefined;
      return this.findById(id);
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn) throw new DuplicateIsbnError(input.isbn);
      throw err;
    }
  }

  delete(id: number): boolean {
    const result = this.db.prepare("DELETE FROM books WHERE id = ?").run(id);
    return result.changes > 0;
  }
}
