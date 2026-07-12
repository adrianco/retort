import sqlite3 from 'sqlite3';
import { Database, open } from 'sqlite';

let db: Database;

async function initializeDatabase() {
  db = await open({
    filename: './books.db',
    driver: sqlite3.Database
  });
  
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
  `);
}

async function getAllBooks(author?: string) {
  let query = 'SELECT * FROM books';
  let params: any[] = [];
  
  if (author) {
    query += ' WHERE author = ?';
    params.push(author);
  }
  
  const result = await db.all(query, params);
  return result;
}

async function getBookById(id: number) {
  const result = await db.get('SELECT * FROM books WHERE id = ?', [id]);
  return result;
}

async function createBook(title: string, author: string, year?: number, isbn?: string) {
  const result = await db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    [title, author, year, isbn]
  );
  return result.lastID as number;
}

async function updateBook(id: number, title?: string, author?: string, year?: number, isbn?: string) {
  let query = 'UPDATE books SET ';
  const params: any[] = [];
  const updates: string[] = [];
  
  if (title !== undefined) {
    updates.push('title = ?');
    params.push(title);
  }
  if (author !== undefined) {
    updates.push('author = ?');
    params.push(author);
  }
  if (year !== undefined) {
    updates.push('year = ?');
    params.push(year);
  }
  if (isbn !== undefined) {
    updates.push('isbn = ?');
    params.push(isbn);
  }
  
  query += updates.join(', ') + ' WHERE id = ?';
  params.push(id);
  
  await db.run(query, params);
}

async function deleteBook(id: number) {
  await db.run('DELETE FROM books WHERE id = ?', [id]);
}

export {
  initializeDatabase,
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook
};
