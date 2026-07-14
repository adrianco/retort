import express, { Application, Request, Response } from 'express';

// In-memory storage for books (for demonstration)
let books: any[] = [];
let nextId = 1;

// Create Express app
const app: Application = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Get all books with optional author filter
app.get('/books', (req: Request, res: Response) => {
  const { author } = req.query;
  
  let filteredBooks = books;
  
  if (author && typeof author === 'string') {
    filteredBooks = books.filter(book => book.author === author);
  }
  
  res.status(200).json(filteredBooks);
});

// Get a single book by ID
app.get('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const book = books.find(b => b.id === id);
  
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  res.status(200).json(book);
});

// Create a new book
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  
  // Validation
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required' 
    });
  }
  
  const newBook = {
    id: nextId++,
    title,
    author,
    year,
    isbn
  };
  
  books.push(newBook);
  res.status(201).json(newBook);
});

// Update a book
app.put('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const { title, author, year, isbn } = req.body;
  
  // Validation
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required' 
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
  
  res.status(200).json(books[bookIndex]);
});

// Delete a book
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const bookIndex = books.findIndex(b => b.id === id);
  
  if (bookIndex === -1) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  books.splice(bookIndex, 1);
  res.status(200).json({ message: 'Book deleted successfully' });
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

export { app };