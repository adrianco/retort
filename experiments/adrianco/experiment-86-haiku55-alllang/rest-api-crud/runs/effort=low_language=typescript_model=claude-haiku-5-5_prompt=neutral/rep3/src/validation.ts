import type { BookInput } from './db.js';

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: Record<string, string> };

/**
 * Validates a request body for creating or replacing a book.
 * Title and author are required non-empty strings; year and isbn are optional.
 */
export function validateBook(body: unknown): ValidationResult {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, errors: { body: 'Request body must be a JSON object' } };
  }
  const data = body as Record<string, unknown>;
  const errors: Record<string, string> = {};

  if (typeof data.title !== 'string' || data.title.trim() === '') {
    errors.title = 'title is required and must be a non-empty string';
  }
  if (typeof data.author !== 'string' || data.author.trim() === '') {
    errors.author = 'author is required and must be a non-empty string';
  }

  let year: number | null = null;
  if (data.year !== undefined && data.year !== null) {
    if (typeof data.year !== 'number' || !Number.isInteger(data.year)) {
      errors.year = 'year must be an integer';
    } else {
      year = data.year;
    }
  }

  let isbn: string | null = null;
  if (data.isbn !== undefined && data.isbn !== null) {
    if (typeof data.isbn !== 'string') {
      errors.isbn = 'isbn must be a string';
    } else {
      isbn = data.isbn.trim();
    }
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: {
      title: (data.title as string).trim(),
      author: (data.author as string).trim(),
      year,
      isbn,
    },
  };
}
