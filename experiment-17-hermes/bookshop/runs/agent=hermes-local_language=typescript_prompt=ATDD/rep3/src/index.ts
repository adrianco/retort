import express from 'express';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';

const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());

// Database setup
let db: any;

async function initDatabase() {
  try {
    db = await open({
      filename: './bookstore.db',
      driver: sqlite3.Database
    });
    
    // Create books table
    await db.exec(`CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )`);
  } catch (error) {
    console.error('Failed to initialize database:', error);
    process.exit(1);
  }
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Get all books
app.get('/books', async (req, res) => {
  try {
    const { author } = req.query;
    let books;
    
    if (author) {
      books = await db.all('SELECT * FROM books WHERE author LIKE ?', `%${author}%`);
    } else {
      books = await db.all('SELECT * FROM books');
    }
    
    res.status(200).json(books);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get book by ID
app.get('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const book = await db.get('SELECT * FROM books WHERE id = ?', id);
    
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// Create new book
app.post('/books', async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validation
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      title, author, year, isbn
    );
    
    const newBook = await db.get('SELECT * FROM books WHERE id = ?', result.lastID);
    res.status(201).json(newBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Update book
app.put('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const { title, author, year, isbn } = req.body;
    
    // Validation
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    const existingBook = await db.get('SELECT * FROM books WHERE id = ?', id);
    
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    await db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      title, author, year, isbn, id
    );
    
    const updatedBook = await db.get('SELECT * FROM books WHERE id = ?', id);
    res.status(200).json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete book
app.delete('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const result = await db.run('DELETE FROM books WHERE id = ?', id);
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

async function startServer() {
  await initDatabase();
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}

startServer().catch(console.error);
