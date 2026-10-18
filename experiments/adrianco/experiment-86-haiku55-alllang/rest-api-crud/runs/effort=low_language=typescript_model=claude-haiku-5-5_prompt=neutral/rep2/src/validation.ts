import type { BookInput } from './db.js';

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: Record<string, string> };

const CURRENT_YEAR_MAX = 3000;

function isBlankString(v: unknown): boolean {
  return typeof v !== 'string' || v.trim().length === 0;
}

/**
 * Validates a request body for creating or updating a book.
 * `title` and `author` are required; `year` and `isbn` are optional.
 */
export function validateBook(body: unknown): ValidationResult {
  const errors: Record<string, string> = {};

  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, errors: { body: 'request body must be a JSON object' } };
  }
  const b = body as Record<string, unknown>;

  if (isBlankString(b.title)) errors.title = 'title is required and must be a non-empty string';
  if (isBlankString(b.author)) errors.author = 'author is required and must be a non-empty string';

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== 'number' || !Number.isInteger(b.year) || b.year < 0 || b.year > CURRENT_YEAR_MAX) {
      errors.year = `year must be an integer between 0 and ${CURRENT_YEAR_MAX}`;
    } else {
      year = b.year;
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== 'string' || b.isbn.trim().length === 0) {
      errors.isbn = 'isbn must be a non-empty string when provided';
    } else {
      isbn = b.isbn.trim();
    }
  }

  if (Object.keys(errors).length > 0) return { ok: false, errors };

  return {
    ok: true,
    value: {
      title: (b.title as string).trim(),
      author: (b.author as string).trim(),
      year,
      isbn,
    },
  };
}

/** Parses a path segment into a positive integer id, or null if invalid. */
export function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}
