import * as sqlite3 from 'sqlite3';
import { getDatabase } from '../database';
import { Book, BookInput } from '../types';

export async function getAllBooks(author?: string): Promise<Book[]> {
  return new Promise((resolve, reject) => {
    const db = getDatabase();
    if (author) {
      db.all('SELECT * FROM books WHERE author = ?', [author], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows as Book[]);
        }
      });
    } else {
      db.all('SELECT * FROM books', (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows as Book[]);
        }
      });
    }
  });
}

export async function getBookById(id: number): Promise<Book | null> {
  return new Promise((resolve, reject) => {
    const db = getDatabase();
    db.get('SELECT * FROM books WHERE id = ?', [id], (err, row) => {
      if (err) {
        reject(err);
      } else {
        resolve(row as Book | null);
      }
    });
  });
}

export async function createBook(book: BookInput): Promise<Book> {
  return new Promise((resolve, reject) => {
    const db = getDatabase();
    db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [book.title, book.author, book.year, book.isbn],
      function (err) {
        if (err) {
          reject(err);
        } else {
          resolve({
            id: this.lastID,
            ...book,
          } as Book);
        }
      }
    );
  });
}

export async function updateBook(id: number, book: BookInput): Promise<Book | null> {
  return new Promise((resolve, reject) => {
    const db = getDatabase();
    db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [book.title, book.author, book.year, book.isbn, id],
      function (err) {
        if (err) {
          reject(err);
        } else {
          if (this.changes === 0) {
            resolve(null);
          } else {
            resolve({ id, ...book } as Book);
          }
        }
      }
    );
  });
}

export async function deleteBook(id: number): Promise<boolean> {
  return new Promise((resolve, reject) => {
    const db = getDatabase();
    db.run('DELETE FROM books WHERE id = ?', [id], function (err) {
      if (err) {
        reject(err);
      } else {
        resolve(this.changes > 0);
      }
    });
  });
}
