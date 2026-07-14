const express = require('express');
const path = require('path');
const { BookService } = require('./bookService');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize book service
const bookService = new BookService(path.join(__dirname, '../books.db'));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// Create a new book
app.post('/books', async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }
    
    const newBook = await bookService.createBook({
      title,
      author,
      year,
      isbn
    });
    
    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Get all books with optional author filter
app.get('/books', async (req, res) => {
  try {
    const { author } = req.query;
    const books = await bookService.getAllBooks(author);
    res.json(books);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const book = await bookService.getBookById(id);
    
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// Update a book
app.put('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required fields' 
      });
    }
    
    const updatedBook = await bookService.updateBook(id, {
      title,
      author,
      year,
      isbn
    });
    
    if (!updatedBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete a book
app.delete('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const deleted = await bookService.deleteBook(id);
    
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.json({ message: 'Book deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

module.exports = app;