const express = require('express');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize database
async function initDb() {
  const db = await open({
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
  
  return db;
}

initDb().catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Get all books with optional author filter
app.get('/books', async (req, res) => {
  try {
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    
    const { author } = req.query;
    
    if (author) {
      const books = await db.all(
        'SELECT * FROM books WHERE author = ? ORDER BY title',
        [author]
      );
      res.status(200).json(books);
    } else {
      const books = await db.all('SELECT * FROM books ORDER BY title');
      res.status(200).json(books);
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch books' });
  }
});

// Get a single book by ID
app.get('/books/:id', async (req, res) => {
  try {
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json(book);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch book' });
  }
});

// Create a new book
app.post('/books', async (req, res) => {
  try {
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields
    if (!title || !author) {
      return res.status(400).json({ error: 'Title and author are required' });
    }
    
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    
    const book = await db.get('SELECT * FROM books WHERE id = ?', [result.lastID]);
    
    if (!book) {
      throw new Error('Failed to create book');
    }
    
    res.status(201).json(book);
  } catch (error) {
    if (error.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'Book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Failed to create book' });
  }
});

// Update a book
app.put('/books/:id', async (req, res) => {
  try {
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    // Check if book exists
    const existingBook = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    if (!existingBook) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    const { title, author, year, isbn } = req.body;
    
    // Validate required fields if provided
    if (title && !title.trim()) {
      return res.status(400).json({ error: 'Title cannot be empty' });
    }
    if (author && !author.trim()) {
      return res.status(400).json({ error: 'Author cannot be empty' });
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
    const updatedBook = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    
    res.status(200).json(updatedBook);
  } catch (error) {
    if (error.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'Book with this ISBN already exists' });
    }
    res.status(500).json({ error: 'Failed to update book' });
  }
});

// Delete a book
app.delete('/books/:id', async (req, res) => {
  try {
    const db = await open({
      filename: './books.db',
      driver: sqlite3.Database
    });
    
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid book ID' });
    }
    
    const result = await db.run('DELETE FROM books WHERE id = ?', [id]);
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json({ message: 'Book deleted successfully' });
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
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

module.exports = app;