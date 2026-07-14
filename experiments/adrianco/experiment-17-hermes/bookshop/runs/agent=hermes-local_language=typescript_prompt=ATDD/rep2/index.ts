import express, { Application, Request, Response, NextFunction } from 'express';
import { DatabaseHelper, Book } from './database';

const app: Application = express();
const port = process.env.PORT ? parseInt(process.env.PORT) : 3000;

// Middleware
app.use(express.json());

// Initialize database
const db = new DatabaseHelper();
db.init().catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Create a new book
app.post('/books', async (req: Request, res: Response) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({
        error: 'Title and author are required'
      });
    }

    const book: Omit<Book, 'id'> = {
      title,
      author,
      year,
      isbn
    };

    const createdBook = await db.createBook(book);
    res.status(201).json(createdBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get all books with optional author filter
app.get('/books', async (req: Request, res: Response) => {
  try {
    const author = req.query.author ? req.query.author.toString() : undefined;
    const books = await db.getAllBooks(author);
    res.json(books);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const book = await db.getBookById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }

    res.json(book);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update a book
app.put('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const { title, author, year, isbn } = req.body;

    // Prepare update data
    const updateData: Partial<Book> = {};
    if (title !== undefined) updateData.title = title;
    if (author !== undefined) updateData.author = author;
    if (year !== undefined) updateData.year = year;
    if (isbn !== undefined) updateData.isbn = isbn;

    const updatedBook = await db.updateBook(id, updateData);
    if (!updatedBook) {
      return res.status(404).json({ error: 'Book not found' });
    }

    res.json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete a book
app.delete('/books/:id', async (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }

    const deleted = await db.deleteBook(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }

    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Handle 404 for undefined routes
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(error);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

export default app;
