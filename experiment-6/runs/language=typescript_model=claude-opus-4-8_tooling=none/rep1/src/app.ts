import express, { Request, Response } from 'express';
import { BookRepository, BookInput } from './db';

interface ValidationResult {
  valid: boolean;
  errors: string[];
  value?: BookInput;
}

/**
 * Validates and normalizes a book payload. `title` and `author` are
 * required non-empty strings; `year` (if present) must be an integer
 * and `isbn` (if present) must be a string.
 */
function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];
  if (typeof body !== 'object' || body === null) {
    return { valid: false, errors: ['Request body must be a JSON object'] };
  }
  const b = body as Record<string, unknown>;

  if (typeof b.title !== 'string' || b.title.trim() === '') {
    errors.push('title is required and must be a non-empty string');
  }
  if (typeof b.author !== 'string' || b.author.trim() === '') {
    errors.push('author is required and must be a non-empty string');
  }
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== 'number' || !Number.isInteger(b.year)) {
      errors.push('year must be an integer');
    }
  }
  if (b.isbn !== undefined && b.isbn !== null && typeof b.isbn !== 'string') {
    errors.push('isbn must be a string');
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    value: {
      title: (b.title as string).trim(),
      author: (b.author as string).trim(),
      year: (b.year as number | null | undefined) ?? null,
      isbn: (b.isbn as string | null | undefined) ?? null,
    },
  };
}

function parseId(raw: string): number | null {
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) return null;
  return id;
}

export function createApp(repo: BookRepository) {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Create
  app.post('/books', (req: Request, res: Response) => {
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const book = repo.create(result.value!);
    res.status(201).json(book);
  });

  // List (with optional ?author= filter)
  app.get('/books', (req: Request, res: Response) => {
    const author =
      typeof req.query.author === 'string' ? req.query.author : undefined;
    res.status(200).json(repo.list(author));
  });

  // Get one
  app.get('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'Invalid book id' });
    }
    const book = repo.getById(id);
    if (!book) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(book);
  });

  // Update
  app.put('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'Invalid book id' });
    }
    const result = validateBook(req.body);
    if (!result.valid) {
      return res.status(400).json({ errors: result.errors });
    }
    const updated = repo.update(id, result.value!);
    if (!updated) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(200).json(updated);
  });

  // Delete
  app.delete('/books/:id', (req: Request, res: Response) => {
    const id = parseId(req.params.id);
    if (id === null) {
      return res.status(400).json({ error: 'Invalid book id' });
    }
    const deleted = repo.delete(id);
    if (!deleted) {
      return res.status(404).json({ error: 'Book not found' });
    }
    res.status(204).send();
  });

  return app;
}
