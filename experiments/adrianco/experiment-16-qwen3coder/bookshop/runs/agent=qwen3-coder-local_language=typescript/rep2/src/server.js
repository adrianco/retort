"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const database_1 = require("./database");
const bookService_1 = require("./bookService");
const app = (0, express_1.default)();
const port = process.env.PORT || 3000;
// Middleware
app.use(express_1.default.json());
// Initialize database
(0, database_1.initDb)().catch(err => {
    console.error('Failed to initialize database:', err);
    process.exit(1);
});
// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});
// Get all books with optional author filter
app.get('/books', async (req, res) => {
    try {
        const { author } = req.query;
        const bookService = new bookService_1.BookService();
        const books = await bookService.getAllBooks(author);
        res.status(200).json(books);
    }
    catch (error) {
        res.status(500).json({ error: 'Failed to fetch books' });
    }
});
// Get a single book by ID
app.get('/books/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({ error: 'Invalid book ID' });
        }
        const bookService = new bookService_1.BookService();
        const book = await bookService.getBookById(id);
        if (!book) {
            return res.status(404).json({ error: 'Book not found' });
        }
        res.status(200).json(book);
    }
    catch (error) {
        res.status(500).json({ error: 'Failed to fetch book' });
    }
});
// Create a new book
app.post('/books', async (req, res) => {
    try {
        const bookService = new bookService_1.BookService();
        const book = await bookService.createBook(req.body);
        res.status(201).json(book);
    }
    catch (error) {
        if (error instanceof Error && error.message.includes('required')) {
            return res.status(400).json({ error: error.message });
        }
        if (error instanceof Error && error.message.includes('already exists')) {
            return res.status(409).json({ error: error.message });
        }
        res.status(500).json({ error: 'Failed to create book' });
    }
});
// Update a book
app.put('/books/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({ error: 'Invalid book ID' });
        }
        const bookService = new bookService_1.BookService();
        const updatedBook = await bookService.updateBook(id, req.body);
        if (!updatedBook) {
            return res.status(404).json({ error: 'Book not found' });
        }
        res.status(200).json(updatedBook);
    }
    catch (error) {
        if (error instanceof Error && error.message.includes('empty')) {
            return res.status(400).json({ error: error.message });
        }
        if (error instanceof Error && error.message.includes('already exists')) {
            return res.status(409).json({ error: error.message });
        }
        res.status(500).json({ error: 'Failed to update book' });
    }
});
// Delete a book
app.delete('/books/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({ error: 'Invalid book ID' });
        }
        const bookService = new bookService_1.BookService();
        const deleted = await bookService.deleteBook(id);
        if (!deleted) {
            return res.status(404).json({ error: 'Book not found' });
        }
        res.status(200).json({ message: 'Book deleted successfully' });
    }
    catch (error) {
        res.status(500).json({ error: 'Failed to delete book' });
    }
});
// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});
// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
exports.default = app;
//# sourceMappingURL=server.js.map