export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type BookInput = {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
};

export type ValidationResult =
  | { ok: true; value: Partial<BookInput> }
  | { ok: false; errors: Record<string, string> };

const MIN_YEAR = 1450; // Gutenberg press era; a sanity floor for book years
const MAX_YEAR = new Date().getFullYear() + 1;

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

/**
 * Validates a request body for create (partial = false) or update (partial = true).
 * On create, title and author are required. On update, any field may be omitted,
 * but a provided title or author must still be a non-empty string.
 */
export function validateBookInput(body: unknown, partial = false): ValidationResult {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) {
    return { ok: false, errors: { body: 'Request body must be a JSON object' } };
  }
  const input = body as Record<string, unknown>;
  const errors: Record<string, string> = {};
  const value: Partial<BookInput> = {};

  if (input.title !== undefined || !partial) {
    if (!isNonEmptyString(input.title)) errors.title = 'title is required and must be a non-empty string';
    else value.title = input.title.trim();
  }
  if (input.author !== undefined || !partial) {
    if (!isNonEmptyString(input.author)) errors.author = 'author is required and must be a non-empty string';
    else value.author = input.author.trim();
  }
  if (input.year !== undefined) {
    if (input.year === null) value.year = null;
    else if (
      typeof input.year !== 'number' ||
      !Number.isInteger(input.year) ||
      input.year < MIN_YEAR ||
      input.year > MAX_YEAR
    ) errors.year = `year must be an integer between ${MIN_YEAR} and ${MAX_YEAR}`;
    else value.year = input.year;
  }
  if (input.isbn !== undefined) {
    if (input.isbn === null) value.isbn = null;
    else if (typeof input.isbn !== 'string' || !/^[0-9Xx-]{10,17}$/.test(input.isbn.trim()))
      errors.isbn = 'isbn must be a valid ISBN-10 or ISBN-13 string';
    else value.isbn = input.isbn.trim();
  }

  return Object.keys(errors).length > 0 ? { ok: false, errors } : { ok: true, value };
}
