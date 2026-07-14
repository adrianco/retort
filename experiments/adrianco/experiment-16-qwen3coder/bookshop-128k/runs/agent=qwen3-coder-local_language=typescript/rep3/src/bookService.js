const sqlite3 = require('sqlite3');
const { open } = require('sqlite');
const path = require('path');

class BookService {
  constructor(dbPath) {
    this.dbPath = dbPath;
    this.db = null;
    this.init();
  }

  async init() {
    try {
      this.db = await open({
        filename: this.dbPath,
        driver: sqlite3.Database
      });
      
      await this.db.exec(`
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          author TEXT NOT NULL,
          year INTEGER,
          isbn TEXT
        )
      `);
    } catch (error) {
      console.error('Error initializing database:', error);
      throw error;
    }
  }

  async createBook(book) {
    const { title, author, year, isbn } = book;
    const result = await this.db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    
    const newBook = {
      id: result.lastID,
      title,
      author,
      year,
      isbn
    };
    
    return newBook;
  }

  async getAllBooks(author) {
    if (author) {
      return await this.db.all(
        'SELECT * FROM books WHERE author LIKE ?',
        [`%${author}%`]
      );
    }
    return await this.db.all('SELECT * FROM books');
  }

  async getBookById(id) {
    const book = await this.db.get('SELECT * FROM books WHERE id = ?', [id]);
    return book || null;
  }

  async updateBook(id, book) {
    const existingBook = await this.getBookById(id);
    if (!existingBook) {
      return null;
    }

    const { title, author, year, isbn } = book;
    const fieldsToUpdate = [];
    const values = [];

    if (title !== undefined) {
      fieldsToUpdate.push('title = ?');
      values.push(title);
    }
    if (author !== undefined) {
      fieldsToUpdate.push('author = ?');
      values.push(author);
    }
    if (year !== undefined) {
      fieldsToUpdate.push('year = ?');
      values.push(year);
    }
    if (isbn !== undefined) {
      fieldsToUpdate.push('isbn = ?');
      values.push(isbn);
    }

    if (fieldsToUpdate.length === 0) {
      return existingBook;
    }

    values.push(id);
    const query = `UPDATE books SET ${fieldsToUpdate.join(', ')} WHERE id = ?`;
    await this.db.run(query, values);

    return {
      ...existingBook,
      ...book
    };
  }

  async deleteBook(id) {
    const result = await this.db.run('DELETE FROM books WHERE id = ?', [id]);
    return result.changes > 0;
  }

  async close() {
    if (this.db) {
      await this.db.close();
    }
  }
}

module.exports = { BookService };