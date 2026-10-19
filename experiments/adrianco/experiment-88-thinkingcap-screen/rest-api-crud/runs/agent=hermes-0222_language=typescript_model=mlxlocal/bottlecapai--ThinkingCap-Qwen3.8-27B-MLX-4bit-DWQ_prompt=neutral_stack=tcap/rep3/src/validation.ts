import type { BookFields } from './db.js';

export const MIN_YEAR = 1000;
export const MAX_YEAR = 2100;
export const MAX_TITLE_LENGTH = 500;
export const MAX_AUTHOR_LENGTH = 200;

const ISBN10_PATTERN = /^[0-9]{9}[0-9Xx]$/;
const ISBN13_PATTERN = /^[0-9]{13}$/;

/**
 * Validate a raw request body against the book rules.
 *
 * - `title` and `author` are required unless `partial` is true (PUT).
 * - `year` is optional; must be an integer between MIN_YEAR and MAX_YEAR.
 * - `isbn` is optional; must be a valid ISBN-10 or ISBN-13 (hyphens and
 *   spaces allowed, stripped before checking).
 *
 * Returns `patch` containing only the keys that were present in the body
 * (sanitized), or null when validation failed. For a full (non-partial)
 * validation, `patch` always contains title and author.
 */
export function validateBookPayload(
  body: unknown,
  options: { partial?: boolean } = {},
): { patch: Partial<BookFields> | null; errors: string[] } {
  const errors: string[] = [];
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { patch: null, errors: ['Request body must be a JSON object'] };
  }
  const raw = body as Record<string, unknown>;
  const partial = options.partial === true;
  const patch: Partial<BookFields> = {};

  if (raw.title !== undefined) {
    if (typeof raw.title !== 'string' || raw.title.trim().length === 0) {
      errors.push('title must be a non-empty string');
    } else if (raw.title.trim().length > MAX_TITLE_LENGTH) {
      errors.push(`title must be at most ${MAX_TITLE_LENGTH} characters`);
    } else {
      patch.title = raw.title.trim();
    }
  } else if (!partial) {
    errors.push('title is required');
  }

  if (raw.author !== undefined) {
    if (typeof raw.author !== 'string' || raw.author.trim().length === 0) {
      errors.push('author must be a non-empty string');
    } else if (raw.author.trim().length > MAX_AUTHOR_LENGTH) {
      errors.push(`author must be at most ${MAX_AUTHOR_LENGTH} characters`);
    } else {
      patch.author = raw.author.trim();
    }
  } else if (!partial) {
    errors.push('author is required');
  }

  if (raw.year !== undefined) {
    if (raw.year === null) {
      // Explicit null clears the field (or means "not set" on create).
      patch.year = null;
    } else if (
      typeof raw.year === 'number' &&
      Number.isInteger(raw.year) &&
      raw.year >= MIN_YEAR &&
      raw.year <= MAX_YEAR
    ) {
      patch.year = raw.year;
    } else {
      errors.push(`year must be an integer between ${MIN_YEAR} and ${MAX_YEAR}`);
    }
  }

  if (raw.isbn !== undefined) {
    if (raw.isbn === null) {
      patch.isbn = null;
    } else if (typeof raw.isbn !== 'string' || raw.isbn.trim().length === 0) {
      errors.push('isbn must be a non-empty string');
    } else {
      const compact = raw.isbn.replace(/[-\s]/g, '');
      if (!ISBN10_PATTERN.test(compact) && !ISBN13_PATTERN.test(compact)) {
        errors.push('isbn must be a valid ISBN-10 or ISBN-13');
      } else {
        patch.isbn = raw.isbn.trim();
      }
    }
  }

  if (
    partial &&
    errors.length === 0 &&
    patch.title === undefined &&
    patch.author === undefined &&
    patch.year === undefined &&
    raw.isbn === undefined
  ) {
    errors.push('provide at least one of: title, author, year, isbn');
  }

  if (errors.length > 0) {
    return { patch: null, errors };
  }
  return { patch, errors };
}
