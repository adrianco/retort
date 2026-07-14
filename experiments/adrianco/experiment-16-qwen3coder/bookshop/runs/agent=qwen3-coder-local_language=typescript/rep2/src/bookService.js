"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BookService = void 0;
const database_1 = require("./database");
class BookService {
    async getAllBooks(author) {
        const db = await (0, database_1.getDb)();
        if (author) {
            return await db.all('SELECT * FROM books WHERE author = ? ORDER BY title', [author]);
        }
        else {
            return await db.all('SELECT * FROM books ORDER BY title');
        }
    }
    async getBookById(id) {
        const db = await (0, database_1.getDb)();
        const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
        return book || null;
    }
    async createBook(bookData) {
        const { title, author, year, isbn } = bookData;
        // Validate required fields
        if (!title || !author) {
            throw new Error('Title and author are required');
        }
        const db = await (0, database_1.getDb)();
        try {
            const result = await db.run('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', [title, author, year, isbn]);
            const book = await this.getBookById(result.lastID);
            if (!book) {
                throw new Error('Failed to create book');
            }
            return book;
        }
        catch (error) {
            if (error instanceof Error && error.message.includes('UNIQUE')) {
                throw new Error('Book with this ISBN already exists');
            }
            throw error;
        }
    }
    async updateBook(id, bookData) {
        const db = await (0, database_1.getDb)();
        // Check if book exists
        const existingBook = await this.getBookById(id);
        if (!existingBook) {
            return null;
        }
        // Validate required fields if provided
        if (bookData.title && !bookData.title.trim()) {
            throw new Error('Title cannot be empty');
        }
        if (bookData.author && !bookData.author.trim()) {
            throw new Error('Author cannot be empty');
        }
        // Build dynamic update query
        const updates = [];
        const values = [];
        if (bookData.title !== undefined) {
            updates.push('title = ?');
            values.push(bookData.title);
        }
        if (bookData.author !== undefined) {
            updates.push('author = ?');
            values.push(bookData.author);
        }
        if (bookData.year !== undefined) {
            updates.push('year = ?');
            values.push(bookData.year);
        }
        if (bookData.isbn !== undefined) {
            updates.push('isbn = ?');
            values.push(bookData.isbn);
        }
        if (updates.length === 0) {
            return existingBook;
        }
        values.push(id);
        const query = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;
        try {
            await db.run(query, values);
            return await this.getBookById(id);
        }
        catch (error) {
            if (error instanceof Error && error.message.includes('UNIQUE')) {
                throw new Error('Book with this ISBN already exists');
            }
            throw error;
        }
    }
    async deleteBook(id) {
        const db = await (0, database_1.getDb)();
        const result = await db.run('DELETE FROM books WHERE id = ?', [id]);
        return result.changes > 0;
    }
}
exports.BookService = BookService;
//# sourceMappingURL=bookService.js.map