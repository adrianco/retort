export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  value?: BookInput;
}

const MIN_YEAR = 1;
const MAX_YEAR = 3000;

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

function isYear(v: unknown): v is number {
  return (
    typeof v === 'number' &&
    Number.isInteger(v) &&
    v >= MIN_YEAR &&
    v <= MAX_YEAR
  );
}

/**
 * Validate a book payload.
 *
 * - Create (partial=false): title and author are required.
 * - Update (partial=true):  every provided field must be valid, and at
 *   least one field must be provided.
 */
export function validateBookInput(body: unknown, partial = false): ValidationResult {
  const errors: string[] = [];
  const data =
    body !== null && typeof body === 'object' && !Array.isArray(body)
      ? (body as Record<string, unknown>)
      : null;

  if (data === null) {
    return { ok: false, errors: ['Request body must be a JSON object'] };
  }

  const value: BookInput = {};

  if ('title' in data) {
    if (isNonEmptyString(data.title)) {
      value.title = data.title.trim();
    } else {
      errors.push('title must be a non-empty string');
    }
  } else if (!partial) {
    errors.push('title is required');
  }

  if ('author' in data) {
    if (isNonEmptyString(data.author)) {
      value.author = data.author.trim();
    } else {
      errors.push('author must be a non-empty string');
    }
  } else if (!partial) {
    errors.push('author is required');
  }

  if ('year' in data) {
    if (isYear(data.year)) {
      value.year = data.year;
    } else {
      errors.push(`year must be an integer between ${MIN_YEAR} and ${MAX_YEAR}`);
    }
  }

  if ('isbn' in data) {
    if (isNonEmptyString(data.isbn)) {
      value.isbn = data.isbn.trim();
    } else {
      errors.push('isbn must be a non-empty string');
    }
  }

  if (partial && Object.keys(value).length === 0 && errors.length === 0) {
    errors.push('At least one field (title, author, year, isbn) must be provided');
  }

  return errors.length > 0 ? { ok: false, errors } : { ok: true, errors, value };
}

/** Parse an :id route parameter. Returns null when it is not a positive integer. */
export function parseId(raw: unknown): number | null {
  if (typeof raw !== 'string') return null;
  if (!/^\d+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
