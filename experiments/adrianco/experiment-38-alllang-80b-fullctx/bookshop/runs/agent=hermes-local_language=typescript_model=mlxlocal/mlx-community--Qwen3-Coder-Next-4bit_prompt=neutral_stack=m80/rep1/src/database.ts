import { Database } from 'sqlite3';
import { promisify } from 'util';

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number;
  isbn: string;
  createdAt: string;
  updatedAt: string;
}

export class DatabaseService {
  private db: Database;
  private getAsync: (sql: string, params?: any[]) => Promise<any>;
  private allAsync: (sql: string, params?: any[]) => Promise<any[]>;
  private runAsync: (sql: string, params?: any[]) => Promise<any>;

  constructor(dbPath: string = ':memory:') {
    this.db = new Database(dbPath);
    this.getAsync = promisify(this.db.get.bind(this.db)) as any;
    this.allAsync = promisify(this.db.all.bind(this.db)) as any;
    this.runAsync = promisify(this.db.run.bind(this.db)) as any;
    
    this.init();
  }

  private init(): void {
    const createTableSql = `
      CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER NOT NULL,
        isbn TEXT NOT NULL,
        createdAt TEXT DEFAULT CURRENT_TIMESTAMP,
        updatedAt TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `;
    this.runAsync(createTableSql).catch((err) => {
      console.error('Error creating table:', err);
    });
  }

  async query<T = any>(sql: string, params: any[] = []): Promise<T> {
    return this.getAsync(sql, params);
  }

  async queryAll<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    return this.allAsync(sql, params);
  }

  async execute(sql: string, params: any[] = []): Promise<any> {
    return this.runAsync(sql, params);
  }

  async createBook(book: Omit<Book, 'id' | 'createdAt' | 'updatedAt'> & { id?: string }): Promise<Book> {
    const id = book.id || require('uuid').v4();
    const now = new Date().toISOString();
    const createdAt = now;
    const updatedAt = now;
    
    const sql = `
      INSERT INTO books (id, title, author, year, isbn, createdAt, updatedAt)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    await this.execute(sql, [
      id,
      book.title,
      book.author,
      book.year,
      book.isbn,
      createdAt,
      updatedAt
    ]);
    
    return { ...book, id, createdAt, updatedAt };
  }

  async getBookById(id: string): Promise<Book | null> {
    const sql = `SELECT * FROM books WHERE id = ?`;
    const result = await this.query<Book>(sql, [id]);
    return result || null;
  }

  async getAllBooks(authorFilter?: string): Promise<Book[]> {
    let sql = `SELECT * FROM books`;
    const params: any[] = [];
    
    if (authorFilter) {
      sql += ` WHERE author = ?`;
      params.push(authorFilter);
    }
    
    return this.queryAll<Book>(sql, params);
  }

  async updateBook(id: string, book: Partial<Book>): Promise<Book | null> {
    const existingBook = await this.getBookById(id);
    if (!existingBook) {
      return null;
    }
    
    const updates: string[] = [];
    const params: any[] = [];
    const now = new Date().toISOString();
    
    if (book.title !== undefined) {
      updates.push('title = ?');
      params.push(book.title);
    }
    if (book.author !== undefined) {
      updates.push('author = ?');
      params.push(book.author);
    }
    if (book.year !== undefined) {
      updates.push('year = ?');
      params.push(book.year);
    }
    if (book.isbn !== undefined) {
      updates.push('isbn = ?');
      params.push(book.isbn);
    }
    
    if (updates.length === 0) {
      return existingBook;
    }
    
    // Add updatedAt and id at the end
    updates.push('updatedAt = ?');
    params.push(now);
    params.push(id);
    
    const sql = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;
    
    await this.execute(sql, params);
    return this.getBookById(id);
  }

  async deleteBook(id: string): Promise<boolean> {
    const existingBook = await this.getBookById(id);
    if (!existingBook) {
      return false;
    }
    
    const sql = `DELETE FROM books WHERE id = ?`;
    const result = await this.execute(sql, [id]);
    // Check if the book still exists
    const remaining = await this.getBookById(id);
    return remaining === null;
  }

  async close(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.close((err) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }
}
