import type { BookInput } from './db';

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  value?: BookInput;
}

export function validateBookInput(body: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, errors: ['Request body must be a JSON object'] };
  }

  const obj = body as Record<string, unknown>;
  const { title, author, year, isbn } = obj;

  if (typeof title !== 'string' || title.trim().length === 0) {
    errors.push('title is required and must be a non-empty string');
  }
  if (typeof author !== 'string' || author.trim().length === 0) {
    errors.push('author is required and must be a non-empty string');
  }

  let yearValue: number | null | undefined;
  if (year === undefined || year === null) {
    yearValue = null;
  } else if (typeof year === 'number' && Number.isInteger(year)) {
    yearValue = year;
  } else {
    errors.push('year must be an integer if provided');
  }

  let isbnValue: string | null | undefined;
  if (isbn === undefined || isbn === null) {
    isbnValue = null;
  } else if (typeof isbn === 'string') {
    isbnValue = isbn;
  } else {
    errors.push('isbn must be a string if provided');
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    errors: [],
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: yearValue ?? null,
      isbn: isbnValue ?? null,
    },
  };
}

export function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}
