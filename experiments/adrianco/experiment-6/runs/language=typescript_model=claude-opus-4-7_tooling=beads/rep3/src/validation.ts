import { NewBook } from './db';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  value?: NewBook;
}

export function validateBook(input: unknown): ValidationResult {
  const errors: string[] = [];

  if (input === null || typeof input !== 'object') {
    return { valid: false, errors: ['request body must be a JSON object'] };
  }

  const body = input as Record<string, unknown>;
  const { title, author, year, isbn } = body;

  if (typeof title !== 'string' || title.trim() === '') {
    errors.push('title is required and must be a non-empty string');
  }
  if (typeof author !== 'string' || author.trim() === '') {
    errors.push('author is required and must be a non-empty string');
  }

  let parsedYear: number | null = null;
  if (year !== undefined && year !== null) {
    if (typeof year !== 'number' || !Number.isInteger(year)) {
      errors.push('year must be an integer when provided');
    } else {
      parsedYear = year;
    }
  }

  let parsedIsbn: string | null = null;
  if (isbn !== undefined && isbn !== null) {
    if (typeof isbn !== 'string') {
      errors.push('isbn must be a string when provided');
    } else {
      parsedIsbn = isbn;
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return {
    valid: true,
    errors: [],
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: parsedYear,
      isbn: parsedIsbn,
    },
  };
}
