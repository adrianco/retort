import express, { Request, Response } from 'express';
import { Database } from '../db/database';

const router = express.Router();
const db = new Database();

// Health check endpoint
router.get('/health', async (req: Request, res: Response) => {
    try {
        await db.getBooks();
        res.status(200).json({ status: 'healthy' });
    } catch (err) {
        res.status(500).json({ status: 'unhealthy', error: (err as Error).message });
    }
});

// Create a new book
router.post('/books', async (req: Request, res: Response) => {
    try {
        const { title, author, year, isbn } = req.body;
        
        if (!title || !author) {
            return res.status(400).json({ error: 'Title and author are required' });
        }
        
        const id = await db.createBook({ title, author, year, isbn });
        res.status(201).json({ id, title, author, year, isbn });
    } catch (err) {
        res.status(500).json({ error: (err as Error).message });
    }
});

// List all books
router.get('/books', async (req: Request, res: Response) => {
    try {
        let author: string | undefined = undefined;
        if (req.query.author) {
            author = Array.isArray(req.query.author) ? (req.query.author as string[])[0] : (req.query.author as string);
        }
        const books = await db.getBooks(author);
        res.json(books);
    } catch (err) {
        res.status(500).json({ error: (err as Error).message });
    }
});

// Get a single book by ID
router.get('/books/:id([0-9]+)', async (req: Request, res: Response) => {
    try {
        const id = parseInt(req.params.id, 10);
        
        const book = await db.getBookById(id);
        if (!book) {
            return res.status(404).json({ error: 'Book not found' });
        }
        
        res.json(book);
    } catch (err) {
        res.status(500).json({ error: (err as Error).message });
    }
});

// Update a book
router.put('/books/:id([0-9]+)', async (req: Request, res: Response) => {
    try {
        const id = parseInt(req.params.id, 10);
        
        const { title, author, year, isbn } = req.body;
        
        if (!title || !author) {
            return res.status(400).json({ error: 'Title and author are required' });
        }
        
        const existingBook = await db.getBookById(id);
        if (!existingBook) {
            return res.status(404).json({ error: 'Book not found' });
        }
        
        await db.updateBook(id, { title, author, year, isbn });
        res.status(200).json({ message: 'Book updated successfully' });
    } catch (err) {
        res.status(500).json({ error: (err as Error).message });
    }
});

// Delete a book
router.delete('/books/:id([0-9]+)', async (req: Request, res: Response) => {
    try {
        const id = parseInt(req.params.id, 10);
        
        const existingBook = await db.getBookById(id);
        if (!existingBook) {
            return res.status(404).json({ error: 'Book not found' });
        }
        
        await db.deleteBook(id);
        res.status(200).json({ message: 'Book deleted successfully' });
    } catch (err) {
        res.status(500).json({ error: (err as Error).message });
    }
});

export default router;
