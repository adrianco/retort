import { NewBook } from './db';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  value?: NewBook;
}

/**
 * Validate and normalize a request body into a NewBook.
 * Rules: title and author are required non-empty strings.
 * year (if present) must be an integer; isbn (if present) must be a string.
 */
export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { valid: false, errors: ['Request body must be a JSON object'] };
  }

  const b = body as Record<string, unknown>;

  const title = b.title;
  if (typeof title !== 'string' || title.trim() === '') {
    errors.push('title is required and must be a non-empty string');
  }

  const author = b.author;
  if (typeof author !== 'string' || author.trim() === '') {
    errors.push('author is required and must be a non-empty string');
  }

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== 'number' || !Number.isInteger(b.year)) {
      errors.push('year must be an integer');
    } else {
      year = b.year;
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== 'string') {
      errors.push('isbn must be a string');
    } else {
      isbn = b.isbn;
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
      year,
      isbn,
    },
  };
}
