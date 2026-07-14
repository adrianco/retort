import express, { Express } from 'express';
import { DatabaseSync } from 'node:sqlite';

export function createApp(db: DatabaseSync): Express {
  const app = express();
  app.use(express.json());

  const getBookById = (id: string) => db.prepare('SELECT * FROM books WHERE id = ?').get(id);

  app.get('/health', (_req, res) => {
    res.status(200).json({ status: 'ok' });
  });

  app.post('/books', (req, res) => {
    const { title, author, year, isbn } = req.body;

    if (!title || !author) {
      res.status(400).json({ error: 'title and author are required' });
      return;
    }

    const result = db
      .prepare('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)')
      .run(title, author, year ?? null, isbn ?? null);

    res.status(201).json(getBookById(String(result.lastInsertRowid)));
  });

  app.get('/books', (req, res) => {
    const { author } = req.query;

    const books =
      typeof author === 'string'
        ? db.prepare('SELECT * FROM books WHERE author = ?').all(author)
        : db.prepare('SELECT * FROM books').all();

    res.status(200).json(books);
  });

  app.get('/books/:id', (req, res) => {
    const book = getBookById(req.params.id);

    if (!book) {
      res.status(404).json({ error: 'book not found' });
      return;
    }

    res.status(200).json(book);
  });

  app.put('/books/:id', (req, res) => {
    const { title, author, year, isbn } = req.body;

    if (!title || !author) {
      res.status(400).json({ error: 'title and author are required' });
      return;
    }

    if (!getBookById(req.params.id)) {
      res.status(404).json({ error: 'book not found' });
      return;
    }

    db.prepare('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?').run(
      title,
      author,
      year ?? null,
      isbn ?? null,
      req.params.id
    );

    res.status(200).json(getBookById(req.params.id));
  });

  app.delete('/books/:id', (req, res) => {
    if (!getBookById(req.params.id)) {
      res.status(404).json({ error: 'book not found' });
      return;
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);

    res.status(204).send();
  });

  return app;
}
