"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const supertest_1 = __importDefault(require("supertest"));
const server_1 = __importDefault(require("./server"));
const database_1 = require("./database");
const bookService_1 = require("./bookService");
beforeAll(async () => {
    // Initialize the database before running tests
    await (0, database_1.initDb)();
});
describe('Book API', () => {
    beforeEach(async () => {
        // Clear the database before each test
        const db = await (0, database_1.initDb)();
        await db.exec('DELETE FROM books');
    });
    describe('GET /health', () => {
        it('should return health status', async () => {
            const response = await (0, supertest_1.default)(server_1.default).get('/health');
            expect(response.status).toBe(200);
            expect(response.body).toHaveProperty('status', 'OK');
        });
    });
    describe('POST /books', () => {
        it('should create a new book', async () => {
            const bookData = {
                title: 'Test Book',
                author: 'Test Author',
                year: 2023,
                isbn: '1234567890'
            };
            const response = await (0, supertest_1.default)(server_1.default)
                .post('/books')
                .send(bookData)
                .expect(201);
            expect(response.body).toHaveProperty('title', bookData.title);
            expect(response.body).toHaveProperty('author', bookData.author);
            expect(response.body).toHaveProperty('year', bookData.year);
            expect(response.body).toHaveProperty('isbn', bookData.isbn);
            expect(response.body).toHaveProperty('id');
        });
        it('should return 400 for missing required fields', async () => {
            const bookData = {
                title: 'Test Book'
                // Missing author
            };
            const response = await (0, supertest_1.default)(server_1.default)
                .post('/books')
                .send(bookData)
                .expect(400);
            expect(response.body).toHaveProperty('error');
        });
    });
    describe('GET /books', () => {
        it('should return all books', async () => {
            const bookService = new bookService_1.BookService();
            await bookService.createBook({
                title: 'Book 1',
                author: 'Author 1',
                year: 2020
            });
            await bookService.createBook({
                title: 'Book 2',
                author: 'Author 2',
                year: 2021
            });
            const response = await (0, supertest_1.default)(server_1.default).get('/books').expect(200);
            expect(response.body).toHaveLength(2);
        });
        it('should filter books by author', async () => {
            const bookService = new bookService_1.BookService();
            await bookService.createBook({
                title: 'Book 1',
                author: 'Author 1',
                year: 2020
            });
            await bookService.createBook({
                title: 'Book 2',
                author: 'Author 2',
                year: 2021
            });
            const response = await (0, supertest_1.default)(server_1.default)
                .get('/books')
                .query({ author: 'Author 1' })
                .expect(200);
            expect(response.body).toHaveLength(1);
            expect(response.body[0]).toHaveProperty('author', 'Author 1');
        });
    });
    describe('GET /books/:id', () => {
        it('should return a book by ID', async () => {
            const bookService = new bookService_1.BookService();
            const createdBook = await bookService.createBook({
                title: 'Test Book',
                author: 'Test Author'
            });
            const response = await (0, supertest_1.default)(server_1.default)
                .get(`/books/${createdBook.id}`)
                .expect(200);
            expect(response.body).toHaveProperty('title', 'Test Book');
            expect(response.body).toHaveProperty('author', 'Test Author');
        });
        it('should return 404 for non-existent book', async () => {
            const response = await (0, supertest_1.default)(server_1.default)
                .get('/books/999')
                .expect(404);
            expect(response.body).toHaveProperty('error', 'Book not found');
        });
    });
    describe('PUT /books/:id', () => {
        it('should update a book', async () => {
            const bookService = new bookService_1.BookService();
            const createdBook = await bookService.createBook({
                title: 'Test Book',
                author: 'Test Author'
            });
            const updateData = {
                title: 'Updated Title',
                year: 2023
            };
            const response = await (0, supertest_1.default)(server_1.default)
                .put(`/books/${createdBook.id}`)
                .send(updateData)
                .expect(200);
            expect(response.body).toHaveProperty('title', 'Updated Title');
            expect(response.body).toHaveProperty('year', 2023);
        });
        it('should return 404 for non-existent book', async () => {
            const updateData = {
                title: 'Updated Title'
            };
            const response = await (0, supertest_1.default)(server_1.default)
                .put('/books/999')
                .send(updateData)
                .expect(404);
            expect(response.body).toHaveProperty('error', 'Book not found');
        });
    });
    describe('DELETE /books/:id', () => {
        it('should delete a book', async () => {
            const bookService = new bookService_1.BookService();
            const createdBook = await bookService.createBook({
                title: 'Test Book',
                author: 'Test Author'
            });
            const response = await (0, supertest_1.default)(server_1.default)
                .delete(`/books/${createdBook.id}`)
                .expect(200);
            expect(response.body).toHaveProperty('message', 'Book deleted successfully');
            // Verify the book is deleted
            const getResponse = await (0, supertest_1.default)(server_1.default)
                .get(`/books/${createdBook.id}`)
                .expect(404);
        });
        it('should return 404 for non-existent book', async () => {
            const response = await (0, supertest_1.default)(server_1.default)
                .delete('/books/999')
                .expect(404);
            expect(response.body).toHaveProperty('error', 'Book not found');
        });
    });
});
//# sourceMappingURL=server.test.js.map