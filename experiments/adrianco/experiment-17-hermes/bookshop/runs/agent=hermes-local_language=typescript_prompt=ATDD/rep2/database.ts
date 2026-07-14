import * as sqlite3 from 'sqlite3';
import { open, Database } from 'sqlite';

export interface Book {
  id?: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export class DatabaseHelper {
  private db: Database | null = null;
  private dbPath: string;

  constructor(dbPath: string = 'books.db') {
    this.dbPath = dbPath;
  }

  async init(): Promise<void> {
    this.db = await open({
      filename: this.dbPath,
      driver: sqlite3.Database
    });

    // Create books table if it doesn't exist
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
      )
    `);
  }

  async getAllBooks(author?: string): Promise<Book[]> {
    if (author) {
      return await this.db.all(
        'SELECT * FROM books WHERE author = ?',
        [author]
      );
    }
    return await this.db.all('SELECT * FROM books');
  }

  async getBookById(id: number): Promise<Book | null> {
    const book = await this.db.get('SELECT * FROM books WHERE id = ?', [id]);
    return book || null;
  }

  async createBook(book: Omit<Book, 'id'>): Promise<Book> {
    const result = await this.db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [book.title, book.author, book.year, book.isbn]
    );
    
    return {
      id: result.lastID,
      ...book
    };
  }

  async updateBook(id: number, book: Partial<Book>): Promise<Book | null> {
    const existingBook = await this.getBookById(id);
    if (!existingBook) {
      return null;
    }

    const fields = Object.keys(book).filter(key => key !== 'id');
    if (fields.length === 0) {
      return existingBook;
    }

    const updates = fields.map(field => `${field} = ?`).join(', ');
    const values = fields.map(field => book[field as keyof Book]);

    await this.db.run(
      `UPDATE books SET ${updates} WHERE id = ?`,
      [...values, id]
    );

    return {
      ...existingBook,
      ...book
    };
  }

  async deleteBook(id: number): Promise<boolean> {
    const result = await this.db.run('DELETE FROM books WHERE id = ?', [id]);
    return result.changes > 0;
  }
}
