import { Router, Request, Response } from 'express';
import Database from 'better-sqlite3';

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export function createBooksRouter(db: Database.Database): Router {
  const router = Router();

  // POST /books — Create a new book
  router.post('/', (req: Request, res: Response) => {
    const { title, author, year, isbn } = req.body;

    if (!title || typeof title !== 'string' || title.trim() === '') {
      return res.status(400).json({ error: 'title is required' });
    }
    if (!author || typeof author !== 'string' || author.trim() === '') {
      return res.status(400).json({ error: 'author is required' });
    }
    if (year !== undefined && year !== null) {
      const yearNum = Number(year);
      if (!Number.isInteger(yearNum) || yearNum < 0 || yearNum > 9999) {
        return res.status(400).json({ error: 'year must be a valid integer between 0 and 9999' });
      }
    }

    const stmt = db.prepare(
      'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)'
    );
    const result = stmt.run(
      title.trim(),
      author.trim(),
      year !== undefined && year !== null ? Number(year) : null,
      isbn ? String(isbn).trim() : null
    );

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid) as Book;
    return res.status(201).json(book);
  });

  // GET /books — List all books (supports ?author= filter)
  router.get('/', (req: Request, res: Response) => {
    const { author } = req.query;

    let books: Book[];
    const authorStr = Array.isArray(author) ? author[0] : author;
    if (authorStr && typeof authorStr === 'string' && authorStr.trim() !== '') {
      books = db.prepare('SELECT * FROM books WHERE author LIKE ? ORDER BY id').all(`%${authorStr.trim()}%`) as Book[];
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY id').all() as Book[];
    }

    return res.status(200).json(books);
  });

  // GET /books/:id — Get a single book by ID
  router.get('/:id', (req: Request, res: Response) => {
    const id = parseInt(String(req.params.id), 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!book) {
      return res.status(404).json({ error: 'book not found' });
    }

    return res.status(200).json(book);
  });

  // PUT /books/:id — Update a book
  router.put('/:id', (req: Request, res: Response) => {
    const id = parseInt(String(req.params.id), 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }

    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }

    const { title, author, year, isbn } = req.body;

    const newTitle = title !== undefined ? title : existing.title;
    const newAuthor = author !== undefined ? author : existing.author;
    const newYear = year !== undefined ? year : existing.year;
    const newIsbn = isbn !== undefined ? isbn : existing.isbn;

    if (!newTitle || typeof newTitle !== 'string' || newTitle.trim() === '') {
      return res.status(400).json({ error: 'title is required' });
    }
    if (!newAuthor || typeof newAuthor !== 'string' || newAuthor.trim() === '') {
      return res.status(400).json({ error: 'author is required' });
    }
    if (newYear !== undefined && newYear !== null) {
      const yearNum = Number(newYear);
      if (!Number.isInteger(yearNum) || yearNum < 0 || yearNum > 9999) {
        return res.status(400).json({ error: 'year must be a valid integer between 0 and 9999' });
      }
    }

    db.prepare(
      `UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = datetime('now') WHERE id = ?`
    ).run(
      newTitle.trim(),
      newAuthor.trim(),
      newYear !== undefined && newYear !== null ? Number(newYear) : null,
      newIsbn ? String(newIsbn).trim() : null,
      id
    );

    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book;
    return res.status(200).json(updated);
  });

  // DELETE /books/:id — Delete a book
  router.delete('/:id', (req: Request, res: Response) => {
    const id = parseInt(String(req.params.id), 10);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'invalid id' });
    }

    const existing = db.prepare('SELECT * FROM books WHERE id = ?').get(id) as Book | undefined;
    if (!existing) {
      return res.status(404).json({ error: 'book not found' });
    }

    db.prepare('DELETE FROM books WHERE id = ?').run(id);
    return res.status(204).send();
  });

  return router;
}
