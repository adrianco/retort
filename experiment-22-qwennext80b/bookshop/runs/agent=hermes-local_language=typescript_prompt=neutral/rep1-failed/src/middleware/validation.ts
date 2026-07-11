import { Request, Response, NextFunction } from 'express';
import { BookInput } from '../types/book';

export function validateBookInput(req: Request, res: Response, next: NextFunction): Response | void {
  const { title, author, year, isbn } = req.body;

  if (!title || typeof title !== 'string' || title.trim() === '') {
    return res.status(400).json({ error: 'Title is required' });
  }

  if (!author || typeof author !== 'string' || author.trim() === '') {
    return res.status(400).json({ error: 'Author is required' });
  }

  if (year === undefined || year === null || typeof year !== 'number') {
    return res.status(400).json({ error: 'Year is required' });
  }

  if (!isbn || typeof isbn !== 'string' || isbn.trim() === '') {
    return res.status(400).json({ error: 'ISBN is required' });
  }

  next();
}

export function validateBookUpdateInput(req: Request, res: Response, next: NextFunction): Response | void {
  const { title, author, year, isbn } = req.body;

  if (title !== undefined && (typeof title !== 'string' || title.trim() === '')) {
    return res.status(400).json({ error: 'Title must be a non-empty string' });
  }

  if (author !== undefined && (typeof author !== 'string' || author.trim() === '')) {
    return res.status(400).json({ error: 'Author must be a non-empty string' });
  }

  if (year !== undefined && year !== null && (typeof year !== 'number')) {
    return res.status(400).json({ error: 'Year must be a number' });
  }

  if (isbn !== undefined && (typeof isbn !== 'string' || isbn.trim() === '')) {
    return res.status(400).json({ error: 'ISBN must be a non-empty string' });
  }

  next();
}
