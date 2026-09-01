import express from 'express';
import type { Request, Response } from 'express';
import { getDb } from './database';

type Book = {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
};

const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  const db = getDb();
  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title, author, year || null, isbn || null);

  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;

  res.status(201).json(book);
});

// List all books with optional author filter
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;
  const db = getDb();

  let books: Book[];
  if (author) {
    books = db.prepare('SELECT * FROM books WHERE author = ?').all(author as string) as Book[];
  } else {
    books = db.prepare('SELECT * FROM books').all() as Book[];
  }

  res.status(200).json(books);
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const db = getDb();
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  res.status(200).json(book);
});

// Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const db = getDb();
  const existingBook: Book | undefined = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!existingBook) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, isbn } = req.body;

  const updateTitle = title !== undefined ? title : existingBook.title;
  const updateAuthor = author !== undefined ? author : existingBook.author;
  const updateYear = year !== undefined ? year : existingBook.year;
  const updateIsbn = isbn !== undefined ? isbn : existingBook.isbn;

  if (!updateTitle || !updateAuthor) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  db.prepare(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
  ).run(updateTitle, updateAuthor, updateYear, updateIsbn, id);

  const updatedBook = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;

  res.status(200).json(updatedBook);
});

// Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }

  const db = getDb();
  const book: Book | undefined = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;

  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  db.prepare('DELETE FROM books WHERE id = ?').run(id);

  res.status(204).send();
});

// Start server
const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

export { app, server };
