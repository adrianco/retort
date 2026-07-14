import express, { Application, Request, Response, NextFunction } from 'express';
import fs from 'fs';
import path from 'path';

// Book type definition
interface Book {
  id?: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

// In-memory storage for books (since we're using simple approach)
let books: Book[] = [];
let nextId = 1;

// Helper to save books to file (as a mock for SQLite)
function saveBooks(): void {
  try {
    fs.writeFileSync('./books.json', JSON.stringify(books, null, 2));
  } catch (error) {
    console.error('Failed to save books:', error);
  }
}

// Helper to load books from file
function loadBooks(): void {
  try {
    if (fs.existsSync('./books.json')) {
      const data = fs.readFileSync('./books.json', 'utf8');
      books = JSON.parse(data);
      if (books.length > 0) {
        nextId = Math.max(...books.map(b => b.id || 0)) + 1;
      }
    }
  } catch (error) {
    console.error('Failed to load books:', error);
    books = [];
    nextId = 1;
  }
}

// Load books on startup
loadBooks();

// Middleware to parse JSON
const app: Application = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({
        error: 'Title and author are required fields'
      });
    }

    const newBook: Book = {
      id: nextId++,
      title,
      author,
      year,
      isbn
    };

    books.push(newBook);
    saveBooks();

    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Get all books with optional author filter
app.get('/books', (req: Request, res: Response) => {
  try {
    const { author } = req.query;
    
    let filteredBooks = books;
    if (author) {
      filteredBooks = books.filter(book => 
        book.author.toLowerCase().includes(author.toString().toLowerCase())
      );
    }

    res.status(200).json(filteredBooks);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const book = books.find(b => b.id === id);

    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const { title, author, year, isbn } = req.body;

    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({
        error: 'Title and author are required fields'
      });
    }

    const bookIndex = books.findIndex(b => b.id === id);
    
    if (bookIndex === -1) {
      return res.status(404).json({ error: 'Book not found' });
    }

    books[bookIndex] = {
      id,
      title,
      author,
      year,
      isbn
    };

    saveBooks();
    res.status(200).json(books[bookIndex]);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const bookIndex = books.findIndex(b => b.id === id);
    
    if (bookIndex === -1) {
      return res.status(404).json({ error: 'Book not found' });
    }

    books.splice(bookIndex, 1);
    saveBooks();
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Route not found' });
});

// Start server
const PORT = process.env.PORT || 3000;
const server = app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

// Export for testing
export { app, server, loadBooks, saveBooks };