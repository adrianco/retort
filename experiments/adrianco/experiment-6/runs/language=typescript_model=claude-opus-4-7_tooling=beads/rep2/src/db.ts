import Database from 'better-sqlite3';

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
  private db: Database.Database;

  constructor(filename: string = ':memory:') {
    this.db = new Database(filename);
    this.db.pragma('journal_mode = WAL');
    this.init();
  }

  private init(): void {
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
    const stmt = this.db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(
      input.title,
      input.author,
      input.year ?? null,
      input.isbn ?? null
    );
    return this.getById(Number(result.lastInsertRowid))!;
  }

  list(author?: string): Book[] {
    if (author) {
      return this.db
        .prepare('SELECT * FROM books WHERE author = ? ORDER BY id')
        .all(author) as Book[];
    }
    return this.db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
  }

  getById(id: number): Book | null {
    const row = this.db.prepare('SELECT * FROM books WHERE id = ?').get(id);
    return (row as Book) ?? null;
  }

  update(id: number, input: BookInput): Book | null {
    const existing = this.getById(id);
    if (!existing) return null;
    this.db
      .prepare(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?'
      )
      .run(
        input.title,
        input.author,
        input.year ?? null,
        input.isbn ?? null,
        id
      );
    return this.getById(id);
  }

  delete(id: number): boolean {
    const result = this.db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return result.changes > 0;
  }

  close(): void {
    this.db.close();
  }
}
