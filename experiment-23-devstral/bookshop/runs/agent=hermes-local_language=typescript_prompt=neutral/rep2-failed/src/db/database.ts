import sqlite3 from 'sqlite3';
import { open, Database as SqliteDatabase } from 'sqlite';

interface Book {
    id?: number;
    title: string;
    author: string;
    year?: number;
    isbn?: string;
}

export class Database {
    db: SqliteDatabase<sqlite3.Database, sqlite3.Statement>;
    
    constructor() {
        // Initialize the db property
        this.db = null as any;
    }
    
    async init(): Promise<void> {
        this.db = await open({
            filename: './books.db',
            driver: sqlite3.Database
        });
        
        await this.db.exec(
            'CREATE TABLE IF NOT EXISTS books (' +
            'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
            'title TEXT NOT NULL,' +
            'author TEXT NOT NULL,' +
            'year INTEGER,' +
            'isbn TEXT)'
        );
    }
    
    async getBooks(author?: string | string[]): Promise<Book[]> {
        let query = 'SELECT * FROM books';
        const params: any[] = [];
        
        if (author) {
            const authorStr = Array.isArray(author) ? author[0] : author;
            query += ' WHERE author = ?';
            params.push(authorStr);
        }
        
        return this.db.all(query, params) as any as Promise<Book[]>;
    }
    
    async getBookById(id: number): Promise<Book | undefined> {
        const row = await this.db.get('SELECT * FROM books WHERE id = ?', [id]) as any as Book;
        return row || undefined;
    }
    
    async createBook(book: Book): Promise<number> {
        const result = await this.db.run(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            [book.title, book.author, book.year, book.isbn]
        );
        return (result as any).lastID;
    }
    
    async updateBook(id: number, book: Book): Promise<void> {
        await this.db.run(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            [book.title, book.author, book.year, book.isbn, id]
        );
    }
    
    async deleteBook(id: number): Promise<void> {
        await this.db.run('DELETE FROM books WHERE id = ?', [id]);
    }
    
    async close(): Promise<void> {
        await this.db.close();
    }
}
