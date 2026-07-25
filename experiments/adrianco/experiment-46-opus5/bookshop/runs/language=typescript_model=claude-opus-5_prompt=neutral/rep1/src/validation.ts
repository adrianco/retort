import type { BookInput, FieldError } from './types.js';

const MAX_TEXT_LENGTH = 512;
const MIN_YEAR = -3000;
const MAX_YEAR = 9999;

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: FieldError[] };

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Validates a required string field: must be a string that is non-empty after
 * trimming. Returns the trimmed value, or null when an error was recorded.
 */
function requiredString(
  field: string,
  raw: unknown,
  errors: FieldError[],
): string | null {
  if (raw === undefined || raw === null) {
    errors.push({ field, message: `${field} is required` });
    return null;
  }
  if (typeof raw !== 'string') {
    errors.push({ field, message: `${field} must be a string` });
    return null;
  }
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    errors.push({ field, message: `${field} must not be empty` });
    return null;
  }
  if (trimmed.length > MAX_TEXT_LENGTH) {
    errors.push({
      field,
      message: `${field} must be at most ${MAX_TEXT_LENGTH} characters`,
    });
    return null;
  }
  return trimmed;
}

/** Validates the optional `year` field. Absent, null or "" all mean "no year". */
function optionalYear(raw: unknown, errors: FieldError[]): number | null {
  if (raw === undefined || raw === null || raw === '') return null;
  if (typeof raw !== 'number' || !Number.isInteger(raw)) {
    errors.push({ field: 'year', message: 'year must be an integer' });
    return null;
  }
  if (raw < MIN_YEAR || raw > MAX_YEAR) {
    errors.push({
      field: 'year',
      message: `year must be between ${MIN_YEAR} and ${MAX_YEAR}`,
    });
    return null;
  }
  return raw;
}

/** Validates the optional `isbn` field. Absent, null or "" all mean "no isbn". */
function optionalIsbn(raw: unknown, errors: FieldError[]): string | null {
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== 'string') {
    errors.push({ field: 'isbn', message: 'isbn must be a string' });
    return null;
  }
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;
  // Accept ISBN-10 / ISBN-13 with optional hyphen or space separators; the
  // final character of an ISBN-10 may be the check digit 'X'.
  const compact = trimmed.replace(/[- ]/g, '');
  if (!/^(?:\d{9}[\dX]|\d{13})$/i.test(compact)) {
    errors.push({
      field: 'isbn',
      message: 'isbn must be a valid ISBN-10 or ISBN-13',
    });
    return null;
  }
  return trimmed;
}

/**
 * Validates a request body for POST /books or PUT /books/:id. Both routes take
 * a complete representation, so the same rules apply to each.
 */
export function validateBookInput(body: unknown): ValidationResult {
  if (!isPlainObject(body)) {
    return {
      ok: false,
      errors: [{ field: 'body', message: 'request body must be a JSON object' }],
    };
  }

  const errors: FieldError[] = [];
  const title = requiredString('title', body['title'], errors);
  const author = requiredString('author', body['author'], errors);
  const year = optionalYear(body['year'], errors);
  const isbn = optionalIsbn(body['isbn'], errors);

  if (errors.length > 0 || title === null || author === null) {
    return { ok: false, errors };
  }
  return { ok: true, value: { title, author, year, isbn } };
}

/** Parses a path `id` parameter, returning null when it is not a positive integer. */
export function parseId(raw: unknown): number | null {
  if (typeof raw !== 'string' || !/^\d+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
