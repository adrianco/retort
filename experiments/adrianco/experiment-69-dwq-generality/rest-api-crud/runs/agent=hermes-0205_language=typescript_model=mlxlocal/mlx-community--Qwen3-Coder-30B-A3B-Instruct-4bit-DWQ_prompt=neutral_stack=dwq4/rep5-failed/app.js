const express = require('express');
const fs = require('fs').promises;

// In-memory storage for books (using file persistence for demonstration)
let books = [];
let nextId = 1;

// Initialize with sample data if file doesn't exist
async function initializeData() {
  try {
    const data = await fs.readFile('books.json', 'utf8');
    const parsed = JSON.parse(data);
    books = parsed;
    if (books.length > 0) {
      nextId = Math.max(...books.map(b => b.id)) + 1;
    }
  } catch (error) {
    // File doesn't exist or is invalid, start fresh with sample data
    books = [
      { id: 1, title: "The Great Gatsby", author: "F. Scott Fitzgerald", year: 1925, isbn: "978-0-7432-7356-5" },
      { id: 2, title: "To Kill a Mockingbird", author: "Harper Lee", year: 1960, isbn: "978-0-06-112008-4" }
    ];
    nextId = 3;
  }
}

// Save data to file
async function saveData() {
  await fs.writeFile('books.json', JSON.stringify(books, null, 2));
}

// Express app setup
const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// GET /books - List all books with optional author filter
app.get('/books', (req, res) => {
  const author = req.query.author;
  
  let filteredBooks = books;
  
  if (author) {
    filteredBooks = books.filter(book => book.author === author);
  }
  
  res.status(200).json(filteredBooks);
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', (req, res) => {
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

// POST /books - Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  // Validation
  if (!title || !author) {
    return res.status(400).json({ 
      error: 'Title and author are required fields' 
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
  
  // Save to file
  saveData().catch(err => console.error('Failed to save data:', err));
  
  res.status(201).json(newBook);
});

// PUT /books/:id - Update a book
app.put('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
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
  
  // Save to file
  saveData().catch(err => console.error('Failed to save data:', err));
  
  res.status(200).json(books[bookIndex]);
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', (req, res) => {
  const id = parseInt(req.params.id);
  
  if (isNaN(id)) {
    return res.status(400).json({ error: 'Invalid book ID' });
  }
  
  const bookIndex = books.findIndex(b => b.id === id);
  
  if (bookIndex === -1) {
    return res.status(404).json({ error: 'Book not found' });
  }
  
  books.splice(bookIndex, 1);
  
  // Save to file
  saveData().catch(err => console.error('Failed to save data:', err));
  
  res.status(200).json({ message: 'Book deleted successfully' });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// Handle 404
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Initialize and start server
async function startServer() {
  await initializeData();
  app.listen(PORT, () => {
    console.log(`Book API server is running on port ${PORT}`);
  });
}

startServer().catch(error => {
  console.error('Failed to start server:', error);
});

module.exports = app;