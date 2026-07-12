import express from 'express';
import bodyParser from 'body-parser';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());

let db: sqlite3.Database;

export async function initializeDB() {
  db = await open({
    filename: './books.db',
    driver: sqlite3.Database
  });

  await db.exec(
    `CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      year INTEGER,
      isbn TEXT
    )`
  );
}

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK' });
});

app.post('/books', async (req, res) => {
  const { title, author, year, isbn } = req.body;
  
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  try {
    const result = await db.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title, author, year, isbn]
    );
    const id = result.lastID;
    res.status(201).json({ id, title, author, year, isbn });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to create book' });
  }
});

app.get('/books', async (req, res) => {
  const { author } = req.query;
  
  try {
    let query = 'SELECT * FROM books';
    const params: any[] = [];
    
    if (author) {
      query += ' WHERE author = ?';
      params.push(author);
    }
    
    const books = await db.all(query, params);
    res.status(200).json(books);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to get books' });
  }
});

app.get('/books/:id', async (req, res) => {
  const { id } = req.params;
  
  try {
    const book = await db.get('SELECT * FROM books WHERE id = ?', [id]);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to get book' });
  }
});

app.put('/books/:id', async (req, res) => {
  const { id } = req.params;
  const { title, author, year, isbn } = req.body;
  
  if (!title || !author) {
    return res.status(400).json({ error: 'Title and author are required' });
  }

  try {
    const result = await db.run(
      'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
      [title, author, year, isbn, id]
    );
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(200).json({ id, title, author, year, isbn });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to update book' });
  }
});

app.delete('/books/:id', async (req, res) => {
  const { id } = req.params;
  
  try {
    const result = await db.run('DELETE FROM books WHERE id = ?', [id]);
    
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Book not found' });
    }
    
    res.status(204).send();
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to delete book' });
  }
});

async function startServer() {
  await initializeDB();
  app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
  });
}

startServer();

export { app };
