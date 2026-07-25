import { Request, Response, NextFunction } from 'express';

export interface BookInput {
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export interface ValidatedRequest<T> extends Request {
  body: T;
}

export function validateBookInput(
  req: ValidatedRequest<BookInput>,
  res: Response,
  next: NextFunction
): void {
  const { title, author, year, isbn } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    res.status(400).json({ error: 'Title is required and must be a non-empty string' });
    return;
  }

  if (!author || typeof author !== 'string' || author.trim() === '') {
    res.status(400).json({ error: 'Author is required and must be a non-empty string' });
    return;
  }

  if (year !== undefined && year !== null && typeof year !== 'number') {
    res.status(400).json({ error: 'Year must be a number if provided' });
    return;
  }

  if (isbn !== undefined && isbn !== null && typeof isbn !== 'string') {
    res.status(400).json({ error: 'ISBN must be a string if provided' });
    return;
  }

  next();
}

export function validateBookUpdate(
  req: ValidatedRequest<BookUpdate>,
  res: Response,
  next: NextFunction
): void {
  const { title, author, year, isbn } = req.body;

  if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
    res.status(400).json({ error: 'Title must be a non-empty string if provided' });
    return;
  }

  if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
    res.status(400).json({ error: 'Author must be a non-empty string if provided' });
    return;
  }

  if (year !== undefined && year !== null && typeof year !== 'number') {
    res.status(400).json({ error: 'Year must be a number if provided' });
    return;
  }

  if (isbn !== undefined && isbn !== null && typeof isbn !== 'string') {
    res.status(400).json({ error: 'ISBN must be a string if provided' });
    return;
  }

  next();
}
