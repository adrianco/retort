import { Request, Response, NextFunction } from 'express';

export interface CreateBookInput {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface UpdateBookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export function validateCreateBook(req: Request, res: Response, next: NextFunction): void {
  const { title, author, year, isbn } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    res.status(400).json({ error: 'Title is required and must be a non-empty string' });
    return;
  }

  if (!author || typeof author !== 'string' || author.trim() === '') {
    res.status(400).json({ error: 'Author is required and must be a non-empty string' });
    return;
  }

  if (year === undefined || year === null || typeof year !== 'number') {
    res.status(400).json({ error: 'Year is required and must be a number' });
    return;
  }

  if (!isbn || typeof isbn !== 'string' || isbn.trim() === '') {
    res.status(400).json({ error: 'ISBN is required and must be a non-empty string' });
    return;
  }

  next();
}

export function validateUpdateBook(req: Request, res: Response, next: NextFunction): void {
  const { title, author, year, isbn } = req.body;
  const hasUpdates = title !== undefined || author !== undefined || year !== undefined || isbn !== undefined;

  if (!hasUpdates) {
    res.status(400).json({ error: 'At least one field (title, author, year, isbn) is required for update' });
    return;
  }

  if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
    res.status(400).json({ error: 'Title must be a non-empty string' });
    return;
  }

  if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
    res.status(400).json({ error: 'Author must be a non-empty string' });
    return;
  }

  if (year !== undefined && (year === null || typeof year !== 'number')) {
    res.status(400).json({ error: 'Year must be a number' });
    return;
  }

  if (isbn !== undefined && (typeof isbn !== 'string' || isbn.trim() === '')) {
    res.status(400).json({ error: 'ISBN must be a non-empty string' });
    return;
  }

  next();
}
