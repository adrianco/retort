import { Book } from "./book";
import sqlite3 from "sqlite3";
import { open } from "sqlite";

export class BookService {
  private db: any;

  constructor() {
    this.init();
  }

  private async init() {
    this.db = await open({
      filename: "./books.db",
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

  async createBook(bookData: Omit<Book, "id">): Promise<Book> {
    const { title, author, year, isbn } = bookData;
    
    // Validate required fields
    if (!title || !author) {
      throw new Error("Title and author are required");
    }
    
    const result = await this.db.run(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
      [title, author, year || null, isbn || null]
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

  async getAllBooks(author?: string): Promise<Book[]> {
    let query = "SELECT * FROM books";
    let params: any[] = [];
    
    if (author) {
      query += " WHERE author = ?";
      params = [author];
    }
    
    const books = await this.db.all(query, params);
    return books;
  }

  async getBookById(id: number): Promise<Book | null> {
    const book = await this.db.get("SELECT * FROM books WHERE id = ?", [id]);
    return book || null;
  }

  async updateBook(id: number, bookData: Partial<Book>): Promise<Book | null> {
    const book = await this.getBookById(id);
    if (!book) {
      return null;
    }
    
    const { title, author, year, isbn } = bookData;
    const fields = [];
    const values: any[] = [];
    
    if (title !== undefined) {
      fields.push("title = ?");
      values.push(title);
    }
    if (author !== undefined) {
      fields.push("author = ?");
      values.push(author);
    }
    if (year !== undefined) {
      fields.push("year = ?");
      values.push(year);
    }
    if (isbn !== undefined) {
      fields.push("isbn = ?");
      values.push(isbn);
    }
    
    if (fields.length === 0) {
      return book;
    }
    
    values.push(id);
    const query = `UPDATE books SET ${fields.join(", ")} WHERE id = ?`;
    
    await this.db.run(query, values);
    
    // Return updated book
    return await this.getBookById(id);
  }

  async deleteBook(id: number): Promise<boolean> {
    const result = await this.db.run("DELETE FROM books WHERE id = ?", [id]);
    return result.changes > 0;
  }
}
