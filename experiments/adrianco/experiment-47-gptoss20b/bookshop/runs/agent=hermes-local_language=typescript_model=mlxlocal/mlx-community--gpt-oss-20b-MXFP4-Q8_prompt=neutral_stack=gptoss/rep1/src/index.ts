import express, { Request, Response } from 'express';
import bodyParser from 'body-parser';
import { getDb } from './database';

const app = express();
app.use(bodyParser.json());
const PORT = 3000;

let dbPromise: Promise<any>;

async function initDb() {
  if (!dbPromise) {
    dbPromise = getDb();
  }
  return dbPromise;
}

// Health check
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// Create book
app.post('/books', async (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;
  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const db = await initDb();
  const result = await db.run(
    'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
    title,
    author,
    year || null,
    isbn || null
  );
  const newBook = await db.get('SELECT * FROM books WHERE id = ?', result.lastID);
  res.status(201).json(newBook);
});

// List books with optional author filter
app.get('/books', async (req: Request, res: Response) => {
  const { author } = req.query;
  const db = await initDb();
  let query = 'SELECT * FROM books';
  const params: any[] = [];
  if (author) {
    query += ' WHERE author = ?';
    params.push(author);
  }
  const books = await db.all(query, params);
  res.json(books);
});

// Get single book
app.get('/books/:id', async (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const db = await initDb();
  const book = await db.get('SELECT * FROM books WHERE id = ?', id);
  if (!book) {
    return res.status(404).json({ error: 'not found' });
  }
  res.json(book);
});

// Update book
app.put('/books/:id', async (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const { title, author, year, isbn } = req.body;
  if (!title || !author) {
    return res.status(400).json({ error: 'title and author are required' });
  }
  const db = await initDb();
  const existing = await db.get('SELECT * FROM books WHERE id = ?', id);
  if (!existing) {
    return res.status(404).json({ error: 'not found' });
  }
  await db.run(
    'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
    title,
    author,
    year || null,
    isbn || null,
    id
  );
  const updated = await db.get('SELECT * FROM books WHERE id = ?', id);
  res.json(updated);
});

// Delete book
app.delete('/books/:id', async (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const db = await initDb();
  const existing = await db.get('SELECT * FROM books WHERE id = ?', id);
  if (!existing) {
    return res.status(404).json({ error: 'not found' });
  }
  await db.run('DELETE FROM books WHERE id = ?', id);
  res.status(204).send();
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

export default app;
