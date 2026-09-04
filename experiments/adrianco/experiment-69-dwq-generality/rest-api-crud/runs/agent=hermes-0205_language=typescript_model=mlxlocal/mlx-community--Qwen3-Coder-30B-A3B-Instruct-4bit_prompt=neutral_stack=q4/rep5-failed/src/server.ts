import express, { Application, Request, Response } from 'express';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import path from 'path';

// Initialize SQLite database
let db: any = null;

// Book interface
interface Book {
  id?: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

// Initialize database
async function initDatabase() {
  const dbPath = path.join(__dirname, '..', 'bookstore.db');
  db = await open({
    driver: sqlite3.Database,
    path: dbPath,
  });

  // Create books table if it doesn't exist
  await db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )
`);
}

// Middleware to parse JSON bodies
const app: Application = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', message: 'Bookstore API is running' });
});

// Get all books with optional author filter
app.get('/books', async (req: Request, res: Response) => {
  try {
    let query = 'SELECT * FROM books';
    let params: any = [];
    
    // Check if author filter is provided
    if (req.query.author) {
      query += ' WHERE author = ?";
      params = [req.query.author as string];
    }

    const books = await db.all(query, params);
    res.status(200).json(books);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create a new book
app.post('/books', async (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    // Insert book into database
    const result = await db.run(
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
    
    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book
app.put('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const { title, author, year, isbn } = req.body;
    
    // Check if book exists
    const existingBook = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Update book
    await db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?', 
      [title, author, year, isbn, id]
    );
    
    const updatedBook = {
      id,
      title,
  author,
  year,
  isbn
    };
    
    res.status(200).json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
app.delete('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const result = await db.run('DELETE FROM books WHERE id = ?', [id]);
    
    if (result.rowsAffected === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, async () => {
  await initDatabase();
  console.log(`Bookstore API server running on port ${PORT}`);
});

export default app;