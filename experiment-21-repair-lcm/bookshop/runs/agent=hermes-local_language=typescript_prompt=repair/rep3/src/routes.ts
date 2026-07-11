import { Router, Request, Response } from 'express';
import { createBook, getAllBooks, getBookById, updateBook, deleteBook, Book } from './db';

const router = Router();

// Input validation
function validateBookInput(body: Record<string, unknown>): { errors: string[]; valid: boolean } {
  const errors: string[] = [];

  if (!body.title || typeof body.title !== 'string' || body.title.trim() === '') {
    errors.push('Title is required and must be a non-empty string');
  }

  if (!body.author || typeof body.author !== 'string' || body.author.trim() === '') {
    errors.push('Author is required and must be a non-empty string');
  }

  if (body.year !== undefined && body.year !== null) {
    if (typeof body.year !== 'number' || !Number.isInteger(body.year) || body.year < 0 || body.year > new Date().getFullYear() + 1) {
      errors.push('Year must be a valid integer between 0 and the current year + 1');
    }
  }

  if (body.isbn !== undefined && body.isbn !== null) {
    if (typeof body.isbn !== 'string') {
      errors.push('ISBN must be a string');
    }
  }

  return { errors, valid: errors.length === 0 };
}

// GET /health
router.get('/health', (_req: Request, res: Response) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// POST /books
router.post('/books', (req: Request, res: Response) => {
  const { valid, errors } = validateBookInput(req.body);

  if (!valid) {
    return res.status(400).json({ errors });
  }

  const { title, author, year, isbn } = req.body;

  const book = createBook(title as string, author as string, year as number | undefined, (isbn as string | undefined) ?? undefined);

  res.status(201).json(book);
});

// GET /books
router.get('/books', (req: Request, res: Response) => {
  const authorFilter = req.query.author as string | undefined;

  const books = getAllBooks(authorFilter);
  res.status(200).json(books);
});

// GET /books/:id
router.get('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Book ID must be a valid integer'] });
  }

  const book = getBookById(id);

  if (!book) {
    return res.status(404).json({ errors: ['Book not found'] });
  }

  res.status(200).json(book);
});

// PUT /books/:id
router.put('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Book ID must be a valid integer'] });
  }

  const existing = getBookById(id);
  if (!existing) {
    return res.status(404).json({ errors: ['Book not found'] });
  }

  const { valid, errors } = validateBookInput(req.body);

  if (!valid) {
    return res.status(400).json({ errors });
  }

  const updated = updateBook(id, {
    title: req.body.title ?? existing.title,
    author: req.body.author ?? existing.author,
    year: req.body.year ?? existing.year,
    isbn: req.body.isbn !== undefined ? (req.body.isbn as string | null) : existing.isbn,
  });

  if (!updated) {
    return res.status(404).json({ errors: ['Book not found'] });
  }

  res.status(200).json(updated);
});

// DELETE /books/:id
router.delete('/books/:id', (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ errors: ['Book ID must be a valid integer'] });
  }

  const deleted = deleteBook(id);

  if (!deleted) {
    return res.status(404).json({ errors: ['Book not found'] });
  }

  res.status(204).send();
});

export { router };
