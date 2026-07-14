import express, { Application, Request, Response, NextFunction } from 'express';
import { Database } from 'sqlite3';
import { open } from 'sqlite';

// Define types
interface Book {
  id?: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

// Initialize express app
const app: Application = express();
const PORT: number = parseInt(process.env.PORT || '3000', 10);

// Middleware
app.use(express.json());

// Initialize database
let db: any;

async function initDB(): Promise<void> {
  try {
    db = await open({
      filename: './books.db',
      driver: Database
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
  } catch (error) {
    console.error('Failed to initialize database:', error);
    process.exit(1);
  }
}

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// GET /books - List all books with optional author filter
app.get('/books', async (req: Request, res: Response) => {
  try {
    const { author } = req.query;
    
    let books: Book[];
    if (author && typeof author === 'string') {
      books = await db.all('SELECT * FROM books WHERE author = ?', [author]);
    } else {
      books = await db.all('SELECT * FROM books');
    }
    
    res.status(200).json(books);
  } catch (error) {
    console.error('Error fetching books:', error);
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const book: Book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    console.error('Error fetching book:', error);
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// POST /books - Create a new book
app.post('/books', async (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validation
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }
    
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    
    const book: Book = {
      id: result.lastID,
      title,
      author,
      year,
      isbn
    };
    
    res.status(201).json(book);
  } catch (error) {
    console.error('Error creating book:', error);
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// PUT /books/:id - Update a book
app.put('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const { title, author, year, isbn } = req.body;
    
    // Validation
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }
    
    const result = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    if (!result) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    await db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year, isbn, id]
    );
    
    const updatedBook: Book = {
      id,
      title,
      author,
      year,
      isbn
    };
    
    res.status(200).json(updatedBook);
  } catch (error) {
    console.error('Error updating book:', error);
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const result = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    if (!result) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    await db.run('DELETE FROM books WHERE id = ?', [id]);
    
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    console.error('Error deleting book:', error);
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
async function startServer(): Promise<void> {
  try {
    await initDB();
    app.listen(PORT, () => {
      console.log(`Server is running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();

export default app;