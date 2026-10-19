import express from 'express';
import { db } from './db';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Create a new book
app.post('/books', (req, res) => {
  const { title, author, year, isbn } = req.body;

  if (!title || !title.toString().trim()) {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || !author.toString().trim()) {
    return res.status(400).json({ error: 'author is required' });
  }

  const stmt = db.prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)');
  const result = stmt.run(title.trim(), author.trim(), year || null, isbn || null);
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
  res.status(201).json(book);
});

// List all books
app.get('/books', (req, res) => {
  const { author } = req.query;
  let books;
  if (author) {
    books = db.prepare('SELECT * FROM books WHERE author = ?').all(author);
  } else {
    books = db.prepare('SELECT * FROM books').all();
  }
  res.json(books);
});

// Get a single book
app.get('/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  res.json(book);
});

// Update a book
app.put('/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }

  const { title, author, year, isbn } = req.body;
  const updates: string[] = [];
  const values: any[] = [];

  if (title !== undefined) {
    if (!title.toString().trim()) {
      return res.status(400).json({ error: 'title must not be empty' });
    }
    updates.push('title = ?');
    values.push(title.trim());
  }
  if (author !== undefined) {
    if (!author.toString().trim()) {
      return res.status(400).json({ error: 'author must not be empty' });
    }
    updates.push('author = ?');
    values.push(author.trim());
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
    return res.status(400).json({ error: 'No valid fields to update' });
  }

  values.push(Number(req.params.id));
  db.prepare(`UPDATE books SET ${updates.join(', ')} WHERE id = ?`).run(...values);
  const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  res.json(updated);
});

// Delete a book
app.delete('/books/:id', (req, res) => {
  const book = db.prepare('SELECT * FROM books WHERE id = ?').get(Number(req.params.id));
  if (!book) {
    return res.status(404).json({ error: 'Book not found' });
  }
  db.prepare('DELETE FROM books WHERE id = ?').run(Number(req.params.id));
  res.status(204).send();
});

const PORT = process.env.PORT || 3000;

if (require.main === module) {
  const server = app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export { app };
