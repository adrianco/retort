import express, { Request, Response } from 'express';
import { db, init, save, getBook, getBooks } from './database';
import { Book, CreateBookInput, UpdateBookInput } from './types';

const app = express();
app.use(express.json());

// --- GET /health ---
app.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok' });
});

// --- POST /books ---
app.post('/books', (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body as CreateBookInput;

  if (!title || !title.trim()) {
    return res.status(400).json({ error: 'title is required' });
  }
  if (!author || !author.trim()) {
    return res.status(400).json({ error: 'author is required' });
  }
  if (!year || typeof year !== 'number' || year < 0) {
    return res.status(400).json({ error: 'valid year is required' });
  }
  if (!isbn || !isbn.trim()) {
    return res.status(400).json({ error: 'isbn is required' });
  }

  try {
    db!.run(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
      [title.trim(), author.trim(), year, isbn.trim()]
    );
    const book = getBook(Number(db!.exec('SELECT last_insert_rowid() as id')[0].values[0][0]));
    save();
    res.status(201).json(book);
  } catch (err: any) {
    if (err.message?.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'isbn already exists' });
    }
    res.status(500).json({ error: 'internal server error' });
  }
});

// --- GET /books ---
app.get('/books', (req: Request, res: Response) => {
  const author = req.query.author as string | undefined;
  const books = getBooks(author);
  res.json(books);
});

// --- GET /books/:id ---
app.get('/books/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const book = getBook(id);

  if (!book) {
    return res.status(404).json({ error: 'book not found' });
  }
  res.json(book);
});

// --- PUT /books/:id ---
app.put('/books/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const existing = getBook(id);

  if (!existing) {
    return res.status(404).json({ error: 'book not found' });
  }

  const body = req.body as UpdateBookInput;
  const { title, author, year, isbn } = body;

  const updates: string[] = [];
  const values: any[] = [];

  if (title !== undefined) {
    if (!title.trim()) return res.status(400).json({ error: 'title cannot be empty' });
    updates.push('title = ?');
    values.push(title.trim());
  }
  if (author !== undefined) {
    if (!author.trim()) return res.status(400).json({ error: 'author cannot be empty' });
    updates.push('author = ?');
    values.push(author.trim());
  }
  if (year !== undefined) {
    if (typeof year !== 'number' || year < 0) return res.status(400).json({ error: 'valid year is required' });
    updates.push('year = ?');
    values.push(year);
  }
  if (isbn !== undefined) {
    if (!isbn.trim()) return res.status(400).json({ error: 'isbn cannot be empty' });
    updates.push('isbn = ?');
    values.push(isbn.trim());
  }

  if (updates.length === 0) {
    return res.status(400).json({ error: 'no valid fields to update' });
  }

  values.push(id);
  const sql = `UPDATE books SET ${updates.join(', ')} WHERE id = ?`;

  try {
    db!.run(sql, values);
    const book = getBook(id);
    save();
    res.json(book);
  } catch (err: any) {
    if (err.message?.includes('UNIQUE constraint failed')) {
      return res.status(409).json({ error: 'isbn already exists' });
    }
    res.status(500).json({ error: 'internal server error' });
  }
});

// --- DELETE /books/:id ---
app.delete('/books/:id', (req: Request, res: Response) => {
  const id = Number(req.params.id);
  const existing = getBook(id);

  if (!existing) {
    return res.status(404).json({ error: 'book not found' });
  }

  db!.run('DELETE FROM books WHERE id = ?', [id]);
  save();
  res.status(204).send();
});

const PORT = process.env.PORT || 3000;

async function start() {
  await init();
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}

start();

export { app };
