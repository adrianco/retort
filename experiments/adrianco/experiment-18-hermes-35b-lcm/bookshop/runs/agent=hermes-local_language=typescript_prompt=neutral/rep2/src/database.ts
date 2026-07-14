import sqlite3 from 'sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

class Database {
  private db: sqlite3.Database;

  constructor(dbPath: string = ':memory:') {
    this.db = new sqlite3.Database(dbPath);
    this.initialize();
  }

  private initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(
        `CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER NOT NULL,
          isbn TEXT NOT NULL UNIQUE
        )`,
        (err) => {
          if (err) {
            reject(err);
          } else {
            resolve();
          }
        }
      );
    });
  }

  private all<T>(sql: string, params: unknown[] = []): Promise<T[]> {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows as T[]);
      });
    });
  }

  private get<T>(sql: string, params: unknown[] = []): Promise<T | null> {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row as T | null);
      });
    });
  }

  private run(sql: string, params: unknown[] = []): Promise<{ lastID: number; changes: number }> {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function (err) {
        if (err) reject(err);
        else resolve({ lastID: this.lastID, changes: this.changes });
      });
    });
  }

  async createBook(
    title: string,
    author: string,
    year: number,
    isbn: string
  ): Promise<Book> {
    await this.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    const book = await this.get<Book>(
      'SELECT * FROM books WHERE isbn = ?',
      [isbn]
    );
    if (!book) throw new Error('Failed to retrieve created book');
    return book;
  }

  async getAllBooks(author?: string): Promise<Book[]> {
    if (author) {
      return this.all<Book>(
        'SELECT * FROM books WHERE author = ?',
        [author]
      );
    }
    return this.all<Book>('SELECT * FROM books');
  }

  async getBookById(id: number): Promise<Book | null> {
    return this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
  }

  async updateBook(
    id: number,
    title?: string,
    author?: string,
    year?: number,
    isbn?: string
  ): Promise<Book | null> {
    const existing = await this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    if (!existing) return null;

    const updates: string[] = [];
    const values: unknown[] = [];

    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    if (author !== undefined) {
      updates.push('author = ?');
      values.push(author);
    }
    if (year !== undefined) {
      updates.push('year = ?');
      values.push(year);
    }
    if (isbn !== undefined) {
      updates.push('isbn = ?');
      values.push(isbn);
    }

    if (updates.length === 0) return existing;

    values.push(id);
    await this.run(
      `UPDATE books SET ${updates.join(', ')} WHERE id = ?`,
      values
    );
    return this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
  }

  async deleteBook(id: number): Promise<boolean> {
    const result = await this.run('DELETE FROM books WHERE id = ?', [id]);
    return result.changes > 0;
  }

  async clearAllBooks(): Promise<void> {
    // Ensure table exists before deleting (handles async initialization race)
    await this.run(
      'CREATE TABLE IF NOT EXISTS books (' +
      'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
      'title TEXT NOT NULL,' +
      'author TEXT NOT NULL,' +
      'year INTEGER NOT NULL,' +
      'isbn TEXT NOT NULL UNIQUE' +
      ')'
    );
    await this.run('DELETE FROM books');
  }

  close(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.close((err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
}

export default Database;
