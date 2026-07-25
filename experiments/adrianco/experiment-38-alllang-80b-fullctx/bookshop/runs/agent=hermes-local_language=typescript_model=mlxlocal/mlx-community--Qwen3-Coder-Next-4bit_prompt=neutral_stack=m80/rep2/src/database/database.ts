import { Database } from 'sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface BookInput {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export class BookDatabase {
  private db: Database;

  constructor(dbPath: string = ':memory:') {
    this.db = new Database(dbPath);
  }

  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.serialize(() => {
        this.db.run(
          `
          CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
          )
        `,
          (err) => {
            if (err) {
              reject(err);
            } else {
              resolve();
            }
          }
        );
      });
    });
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

  async getAllBooks(author?: string): Promise<Book[]> {
    return new Promise((resolve, reject) => {
      const query = author
        ? 'SELECT * FROM books WHERE author = ?'
        : 'SELECT * FROM books';
      const params = author ? [author] : [];

      this.db.all(query, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(
            (rows as Book[]).map((row) => ({
              id: row.id,
              title: row.title,
              author: row.author,
              year: row.year,
              isbn: row.isbn,
            }))
          );
        }
      });
    });
  }

  async getBookById(id: number): Promise<Book | null> {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(
            row
              ? {
                  id: (row as Book).id,
                  title: (row as Book).title,
                  author: (row as Book).author,
                  year: (row as Book).year,
                  isbn: (row as Book).isbn,
                }
              : null
          );
        }
      });
    });
  }

  async createBook(data: BookInput): Promise<Book> {
    return new Promise((resolve, reject) => {
      const { title, author, year, isbn } = data;
      this.db.run(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        [title, author, year, isbn],
        function (err) {
          if (err) {
            reject(err);
          } else {
            resolve({
              id: this.lastID,
              title,
              author,
              year,
              isbn,
            });
          }
        }
      );
    });
  }

  async updateBook(id: number, data: BookUpdate): Promise<Book | null> {
    return new Promise(async (resolve, reject) => {
      const existingBook = await this.getBookById(id);
      if (!existingBook) {
        resolve(null);
        return;
      }

      const { title, author, year, isbn } = {
        ...existingBook,
        ...data,
      };

      this.db.run(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        [title, author, year, isbn, id],
        function (err) {
          if (err) {
            reject(err);
          } else {
            resolve({
              id,
              title,
              author,
              year,
              isbn,
            });
          }
        }
      );
    });
  }

  async deleteBook(id: number): Promise<boolean> {
    return new Promise((resolve, reject) => {
      this.db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
        if (err) {
          reject(err);
        } else {
          resolve(this.changes > 0);
        }
      });
    });
  }
}
