import express from 'express';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

// Initialize database
let db: any;

async function initDatabase() {
  db = await open({
    filename: './books.db',
    driver: sqlite3.Database
  });

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

// Create Express app
const app = express();
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

// Create a new book
app.post('/books', async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required' 
      });
    }
    
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year || null, isbn || null]
    );
    
    const book = await db.get('SELECT * FROM books WHERE id = ?', [result.lastID]);
    res.status(201).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Get all books with optional author filter
app.get('/books', async (req, res) => {
  try {
    const { author } = req.query;
    
    if (author) {
      const books = await db.all('SELECT * FROM books WHERE author LIKE ?', [`%${author}%`]);
      res.json(books);
    } else {
      const books = await db.all('SELECT * FROM books');
      res.json(books);
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
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
    const { id } = req.params;
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ 
        error: 'Title and author are required' 
      });
    }
    
    const result = await db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year || null, isbn || null, id]
    );
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    const updatedBook = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    res.json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete a book
app.delete('/books/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await db.run('DELETE FROM books WHERE id = ?', [id]);
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
async function startServer() {
  await initDatabase();
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}

startServer().catch(console.error);

export { app };
