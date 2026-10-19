import { Request, Response, NextFunction } from 'express';
import { ValidationError } from './types';

export function validateBook(input: any): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!input.title || typeof input.title !== 'string' || input.title.trim() === '') {
    errors.push({ field: 'title', message: 'Title is required and must be a non-empty string' });
  }

  if (!input.author || typeof input.author !== 'string' || input.author.trim() === '') {
    errors.push({ field: 'author', message: 'Author is required and must be a non-empty string' });
  }

  if (input.year === undefined || input.year === null) {
    errors.push({ field: 'year', message: 'Year is required' });
  } else if (!Number.isInteger(input.year) || input.year < 0 || input.year > new Date().getFullYear() + 1) {
    errors.push({ field: 'year', message: 'Year must be a valid integer' });
  }

  if (!input.isbn || typeof input.isbn !== 'string' || input.isbn.trim() === '') {
    errors.push({ field: 'isbn', message: 'ISBN is required and must be a non-empty string' });
  }

  return errors;
}

export function validatePartialBook(input: any): ValidationError[] {
  const errors: ValidationError[] = [];

  if (input.title !== undefined) {
    if (typeof input.title !== 'string' || input.title.trim() === '') {
      errors.push({ field: 'title', message: 'Title must be a non-empty string' });
    }
  }

  if (input.author !== undefined) {
    if (typeof input.author !== 'string' || input.author.trim() === '') {
      errors.push({ field: 'author', message: 'Author must be a non-empty string' });
    }
  }

  if (input.year !== undefined) {
    if (!Number.isInteger(input.year) || input.year < 0 || input.year > new Date().getFullYear() + 1) {
      errors.push({ field: 'year', message: 'Year must be a valid integer' });
    }
  }

  if (input.isbn !== undefined) {
    if (typeof input.isbn !== 'string' || input.isbn.trim() === '') {
      errors.push({ field: 'isbn', message: 'ISBN must be a non-empty string' });
    }
  }

  return errors;
}

export function handleError(err: any, req: Request, res: Response, next: NextFunction) {
  if (err.type === 'validation') {
    return res.status(400).json({ error: 'Validation error', details: err.details });
  }
  if (err.type === 'not_found') {
    return res.status(404).json({ error: err.message });
  }
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
}

export function parseBody(req: Request, res: Response, next: NextFunction) {
  const contentType = req.headers['content-type'];
  if (contentType && contentType.includes('application/json')) {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        req.body = body ? JSON.parse(body) : {};
        next();
      } catch (e) {
        next(new Error('Invalid JSON'));
      }
    });
  } else {
    next();
  }
}
