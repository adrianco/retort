import { DatabaseSync } from "node:sqlite";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type BookInput = Omit<Book, "id">;

export class BookRepository {
  private db: DatabaseSync;

  constructor(path = ":memory:") {
    this.db = new DatabaseSync(path);
    this.db.exec(`CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )`);
  }

  list(author?: string): Book[] {
    if (author) {
      return this.db.prepare("SELECT * FROM books WHERE author = ? ORDER BY id").all(author) as unknown as Book[];
    }
    return this.db.prepare("SELECT * FROM books ORDER BY id").all() as unknown as Book[];
  }

  get(id: number): Book | undefined {
    return this.db.prepare("SELECT * FROM books WHERE id = ?").get(id) as unknown as Book | undefined;
  }

  create(b: BookInput): Book {
    const r = this.db
      .prepare("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)")
      .run(b.title, b.author, b.year, b.isbn);
    return this.get(Number(r.lastInsertRowid))!;
  }

  update(id: number, b: BookInput): Book | undefined {
    const r = this.db
      .prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?")
      .run(b.title, b.author, b.year, b.isbn, id);
    return r.changes ? this.get(id) : undefined;
  }

  delete(id: number): boolean {
    return this.db.prepare("DELETE FROM books WHERE id = ?").run(id).changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
