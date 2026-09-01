const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'books.db');

const db = new Database(DB_PATH);

db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER NOT NULL,
    isbn TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  )
`);

function getAllBooks(author) {
  if (author) {
    const stmt = db.prepare('SELECT * FROM books WHERE author = ? ORDER BY created_at DESC');
    return stmt.all(author);
  }
  const stmt = db.prepare('SELECT * FROM books ORDER BY created_at DESC');
  return stmt.all();
}

function getBookById(id) {
  const stmt = db.prepare('SELECT * FROM books WHERE id = ?');
  return stmt.get(id);
}

function createBook(dto) {
  const stmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
  );
  const result = stmt.run(dto.title, dto.author, dto.year, dto.isbn);
  return getBookById(result.lastInsertRowid);
}

function updateBook(id, dto) {
  const existing = getBookById(id);
  if (!existing) {
    return undefined;
  }

  const updates = [];
  const values = [];

  if (dto.title !== undefined) {
    updates.push('title = ?');
    values.push(dto.title);
  }
  if (dto.author !== undefined) {
    updates.push('author = ?');
    values.push(dto.author);
  }
  if (dto.year !== undefined) {
    updates.push('year = ?');
    values.push(dto.year);
  }
  if (dto.isbn !== undefined) {
    updates.push('isbn = ?');
    values.push(dto.isbn);
  }

  if (updates.length > 0) {
    updates.push("updated_at = datetime('now')");
    values.push(id);
    db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`).run(...values);
  }

  return getBookById(id);
}

function deleteBook(id) {
  const stmt = db.prepare('DELETE FROM books WHERE id = ?');
  const result = stmt.run(id);
  return result.changes > 0;
}

function closeDb() {
  db.close();
}

function cleanDatabase() {
  db.exec('DELETE FROM books');
  db.exec("DELETE FROM sqlite_sequence WHERE name='books'");
}

module.exports = { getAllBooks, getBookById, createBook, updateBook, deleteBook, closeDb, cleanDatabase };
