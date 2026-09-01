import type { BookInput } from './db.js';

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] };

export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, errors: ['request body must be a JSON object'] };
  }
  const b = body as Record<string, unknown>;

  const title = typeof b.title === 'string' ? b.title.trim() : '';
  if (!title) errors.push('title is required and must be a non-empty string');

  const author = typeof b.author === 'string' ? b.author.trim() : '';
  if (!author) errors.push('author is required and must be a non-empty string');

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== 'number' || !Number.isInteger(b.year) || b.year < 0 || b.year > 9999) {
      errors.push('year must be an integer between 0 and 9999');
    } else {
      year = b.year;
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== 'string' || !/^[0-9Xx-]{10,17}$/.test(b.isbn.trim())) {
      errors.push('isbn must be a 10 to 13 digit string (hyphens allowed)');
    } else {
      isbn = b.isbn.trim();
    }
  }

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, value: { title, author, year, isbn } };
}

export function parseId(raw: string): number | undefined {
  if (!/^\d+$/.test(raw)) return undefined;
  const id = Number(raw);
  return Number.isSafeInteger(id) ? id : undefined;
}
