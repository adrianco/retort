import { Router } from 'express';
import type { Database } from 'better-sqlite3';
import { parseId, validateBookInput } from './validate';
import type { Book } from './validate';

export function booksRouter(db: Database): Router {
  const router = Router();

  const insertStmt = db.prepare(
    'INSERT INTO books (title, author, year, isbn) VALUES (@title, @author, @year, @isbn)'
  );
  const selectByIdStmt = db.prepare('SELECT * FROM books WHERE id = ?');
  const selectAllStmt = db.prepare('SELECT * FROM books ORDER BY id');
  const selectByAuthorStmt = db.prepare(
    'SELECT * FROM books WHERE lower(author) = lower(?) ORDER BY id'
  );
  const updateStmt = db.prepare(
    'UPDATE books SET title = @title, author = @author, year = @year, isbn = @isbn WHERE id = @id'
  );
  const deleteStmt = db.prepare('DELETE FROM books WHERE id = ?');

  // POST /books — create a book
  router.post('/', (req, res) => {
    const result = validateBookInput(req.body, false);
    if (!result.ok || !result.value) {
      res.status(400).json({ error: 'Validation failed', details: result.errors });
      return;
    }
    const { title, author } = result.value;
    const year = result.value.year ?? null;
    const isbn = result.value.isbn ?? null;
    const info = insertStmt.run({ title, author, year, isbn });
    const book = selectByIdStmt.get(info.lastInsertRowid) as Book;
    res.status(201).json(book);
  });

  // GET /books — list all books, optional ?author= filter (case-insensitive)
  router.get('/', (req, res) => {
    const author = req.query.author;
    let books: Book[];
    if (typeof author === 'string' && author.trim().length > 0) {
      books = selectByAuthorStmt.all(author.trim()) as Book[];
    } else {
      books = selectAllStmt.all() as Book[];
    }
    res.json(books);
  });

  // GET /books/:id — get one book
  router.get('/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const book = selectByIdStmt.get(id) as Book | undefined;
    if (!book) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    res.json(book);
  });

  // PUT /books/:id — update a book (partial update: provided fields only)
  router.put('/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const existing = selectByIdStmt.get(id) as Book | undefined;
    if (!existing) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    const result = validateBookInput(req.body, true);
    if (!result.ok || !result.value) {
      res.status(400).json({ error: 'Validation failed', details: result.errors });
      return;
    }
    const v = result.value;
    updateStmt.run({
      id,
      title: v.title ?? existing.title,
      author: v.author ?? existing.author,
      year: v.year !== undefined ? v.year : existing.year,
      isbn: v.isbn !== undefined ? v.isbn : existing.isbn,
    });
    res.json(selectByIdStmt.get(id) as Book);
  });

  // DELETE /books/:id — delete a book
  router.delete('/:id', (req, res) => {
    const id = parseId(req.params.id);
    if (id === null) {
      res.status(400).json({ error: 'id must be a positive integer' });
      return;
    }
    const info = deleteStmt.run(id);
    if (info.changes === 0) {
      res.status(404).json({ error: `Book ${id} not found` });
      return;
    }
    res.status(204).send();
  });

  return router;
}
