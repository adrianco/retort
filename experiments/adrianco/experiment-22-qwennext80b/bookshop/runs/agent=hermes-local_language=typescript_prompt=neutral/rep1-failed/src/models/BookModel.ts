import sqlite3 from 'sqlite3';
import { Book, BookInput } from '../types/book';
import { promisify } from 'util';

const dbPath = process.env.DB_PATH || './books.db';

export class BookModel {
  private db: sqlite3.Database | null = null;
  private initialized = false;

  constructor() {
    // Don't initialize in constructor for tests
    if (process.env.RUN_TESTS !== 'true') {
      this.db = new sqlite3.Database(dbPath);
      this.init();
    }
  }

  private async init(): Promise<void> {
    if (!this.db) return;
    await this.run(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        isbn TEXT NOT NULL
      )
    `);
    this.initialized = true;
  }

  public async ensureInitialized(): Promise<void> {
    if (!this.initialized && !this.db) {
      this.db = new sqlite3.Database(dbPath);
    }
    if (!this.initialized) {
      await this.init();
    }
  }

  public run(sql: string, params?: any[]): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        this.db = new sqlite3.Database(dbPath);
        this.init().then(() => {
          this.db!.run(sql, params || [], function (err: Error | null) {
            if (err) reject(err);
            else resolve(this);
          });
        }).catch(reject);
        return;
      }
      this.db.run(sql, params || [], function (err: Error | null) {
        if (err) reject(err);
        else resolve(this);
      });
    });
  }

  private all<T = any>(sql: string, params?: any[]): Promise<T[]> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        this.db = new sqlite3.Database(dbPath);
        this.init().then(() => {
          this.db!.all(sql, params || [], (err: Error | null, rows: T[]) => {
            if (err) reject(err);
            else resolve(rows);
          });
        }).catch(reject);
        return;
      }
      this.db.all(sql, params || [], (err: Error | null, rows: T[]) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  private get<T = any>(sql: string, params?: any[]): Promise<T | undefined> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        this.db = new sqlite3.Database(dbPath);
        this.init().then(() => {
          this.db!.get(sql, params || [], (err: Error | null, row: T | undefined) => {
            if (err) reject(err);
            else resolve(row);
          });
        }).catch(reject);
        return;
      }
      this.db.get(sql, params || [], (err: Error | null, row: T | undefined) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  async findAll(author?: string): Promise<Book[]> {
    await this.ensureInitialized();
    if (author) {
      const books = await this.all<Book>('SELECT * FROM books WHERE author = ?', [author]);
      return books;
    }
    const books = await this.all<Book>('SELECT * FROM books');
    return books;
  }

  async findById(id: number): Promise<Book | undefined> {
    await this.ensureInitialized();
    const book = await this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    return book;
  }

  async create(book: BookInput): Promise<Book> {
    await this.ensureInitialized();
    const result = await this.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [book.title, book.author, book.year, book.isbn]
    );
    const newBook = await this.get<Book>('SELECT * FROM books WHERE id = ?', [result.lastID]);
    return newBook!;
  }

  async update(id: number, book: Partial<BookInput>): Promise<Book | undefined> {
    await this.ensureInitialized();
    const existingBook = await this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    if (!existingBook) return undefined;

    const title = book.title ?? existingBook.title;
    const author = book.author ?? existingBook.author;
    const year = book.year ?? existingBook.year;
    const isbn = book.isbn ?? existingBook.isbn;

    await this.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year, isbn, id]
    );

    const updatedBook = await this.get<Book>('SELECT * FROM books WHERE id = ?', [id]);
    return updatedBook;
  }

  async delete(id: number): Promise<boolean> {
    await this.ensureInitialized();
    const result = await this.run('DELETE FROM books WHERE id = ?', [id]);
    return result.changes > 0;
  }
}
