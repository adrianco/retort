const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { open } = require('sqlite');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
let db;

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
      isbn TEXT UNIQUE
    )
  `);
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Book API is running' });
});

// GET /books - List all books or filter by author
app.get('/books', async (req, res) => {
  try {
    const author = req.query.author;
    if (author) {
      const books = await db.all('SELECT * FROM books WHERE author = ?', author);
      res.status(200).json(books);
    } else {
      const books = await db.all('SELECT * FROM books');
      res.status(200).json(books);
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// GET /books/:id - Get a single book by ID
app.get('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const book = await db.get('SELECT * FROM books WHERE id = ?', id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// POST /books - Create a new book
app.post('/books', async (req, res) => {
  try {
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      title,
      author,
      year || null,
      isbn || null
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
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// PUT /books/:id - Update a book
app.put('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (title && !title.trim()) {
      return res.status(400).json({ error: 'Title cannot be empty' });
    }
    if (author && !author.trim()) {
      return res.status(400).json({ error: 'Author cannot be empty' });
    }
    
    // Check if book exists
    const existingBook = await db.get('SELECT * FROM books WHERE id = ?', id);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    // Build dynamic update query
    const updates = [];
    const values = [];
    
    if (title !== undefined) {
      updates.push('title = ?');
      values.push(title);
    }
    if (author !== undefined) {
      updates.push('author = ?');
      values.push(author);
    }
    if (year !== undefined) {
      updates.push('year = ?');
      values.push(year);
    }
    if (isbn !== undefined) {
      updates.push('isbn = ?');
      values.push(isbn);
    }
    
    if (updates.length === 0) {
      return res.status(200).json(existingBook);
    }
    
    values.push(id);
    const query = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;
    
    await db.run(query, values);
    
    // Return updated book
    const updatedBook = { ...existingBook, ...req.body };
    res.status(200).json(updatedBook);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// DELETE /books/:id - Delete a book
app.delete('/books/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const result = await db.run('DELETE FROM books WHERE id = ?', id);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json({ message: 'Book deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Error handling middleware
app.use((error, req, res) => {
  console.error(error);
  res.status(500).json({ error: 'Internal server error' });
});

// Start the server
async function startServer() {
  await initDatabase();
  console.log('Database initialized successfully');
  
  app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
  });
}

startServer().catch(console.error);
