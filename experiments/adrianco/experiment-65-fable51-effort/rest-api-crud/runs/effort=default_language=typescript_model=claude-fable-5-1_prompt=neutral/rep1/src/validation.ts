import type { BookInput } from "./db.js";

export interface FieldError {
  field: string;
  message: string;
}

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: FieldError[] };

const MAX_TEXT_LENGTH = 500;
const MIN_YEAR = -3000;
const MAX_YEAR = new Date().getUTCFullYear() + 5;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Strips hyphens/spaces and upper-cases the check digit, e.g. "0-306-40615-2" -> "0306406152". */
export function normalizeIsbn(raw: string): string {
  return raw.replace(/[-\s]/g, "").toUpperCase();
}

/** Accepts ISBN-10 (9 digits + digit/X) or ISBN-13 (13 digits), hyphens/spaces allowed. */
export function isValidIsbn(raw: string): boolean {
  const s = normalizeIsbn(raw);
  if (/^\d{13}$/.test(s)) {
    const sum = [...s].reduce(
      (acc, ch, i) => acc + Number(ch) * (i % 2 === 0 ? 1 : 3),
      0,
    );
    return sum % 10 === 0;
  }
  if (/^\d{9}[\dX]$/.test(s)) {
    const sum = [...s].reduce((acc, ch, i) => {
      const v = ch === "X" ? 10 : Number(ch);
      return acc + v * (10 - i);
    }, 0);
    return sum % 11 === 0;
  }
  return false;
}

function requiredText(
  body: Record<string, unknown>,
  field: string,
  errors: FieldError[],
): string | undefined {
  const value = body[field];
  if (value === undefined || value === null) {
    errors.push({ field, message: `${field} is required` });
    return undefined;
  }
  if (typeof value !== "string") {
    errors.push({ field, message: `${field} must be a string` });
    return undefined;
  }
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    errors.push({ field, message: `${field} must not be empty` });
    return undefined;
  }
  if (trimmed.length > MAX_TEXT_LENGTH) {
    errors.push({ field, message: `${field} must be at most ${MAX_TEXT_LENGTH} characters` });
    return undefined;
  }
  return trimmed;
}

/**
 * Validates a request body for creating or fully replacing a book.
 * `title` and `author` are required; `year` and `isbn` are optional (null when omitted).
 */
export function validateBookInput(body: unknown): ValidationResult {
  if (!isPlainObject(body)) {
    return { ok: false, errors: [{ field: "body", message: "request body must be a JSON object" }] };
  }

  const errors: FieldError[] = [];
  const title = requiredText(body, "title", errors);
  const author = requiredText(body, "author", errors);

  let year: number | null = null;
  if (body.year !== undefined && body.year !== null) {
    if (typeof body.year !== "number" || !Number.isInteger(body.year)) {
      errors.push({ field: "year", message: "year must be an integer" });
    } else if (body.year < MIN_YEAR || body.year > MAX_YEAR) {
      errors.push({ field: "year", message: `year must be between ${MIN_YEAR} and ${MAX_YEAR}` });
    } else {
      year = body.year;
    }
  }

  let isbn: string | null = null;
  if (body.isbn !== undefined && body.isbn !== null) {
    if (typeof body.isbn !== "string") {
      errors.push({ field: "isbn", message: "isbn must be a string" });
    } else {
      const trimmed = body.isbn.trim();
      if (trimmed.length === 0) {
        errors.push({ field: "isbn", message: "isbn must not be empty" });
      } else if (!isValidIsbn(trimmed)) {
        errors.push({ field: "isbn", message: "isbn must be a valid ISBN-10 or ISBN-13" });
      } else {
        isbn = normalizeIsbn(trimmed);
      }
    }
  }

  if (errors.length > 0 || title === undefined || author === undefined) {
    return { ok: false, errors };
  }
  return { ok: true, value: { title, author, year, isbn } };
}

/** Parses a path parameter as a positive integer ID, or returns undefined. */
export function parseId(raw: string | undefined): number | undefined {
  if (raw === undefined || !/^\d+$/.test(raw)) return undefined;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : undefined;
}
