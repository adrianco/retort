import type { BookInput, ValidationError } from "./types.js";

const MAX_TEXT_LENGTH = 500;
const MIN_YEAR = -5000;
const MAX_YEAR = 3000;
// Accepts ISBN-10 and ISBN-13 with optional hyphens/spaces; the final ISBN-10
// digit may be an X check character.
const ISBN_PATTERN = /^(?:\d[\s-]*){9}(?:\d|X|x)$|^(?:\d[\s-]*){13}$/;

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: ValidationError[] };

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validateRequiredString(
  body: Record<string, unknown>,
  field: "title" | "author",
  errors: ValidationError[],
): string | undefined {
  const raw = body[field];
  if (raw === undefined || raw === null) {
    errors.push({ field, message: `${field} is required` });
    return undefined;
  }
  if (typeof raw !== "string") {
    errors.push({ field, message: `${field} must be a string` });
    return undefined;
  }
  const trimmed = raw.trim();
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

function validateYear(body: Record<string, unknown>, errors: ValidationError[]): number | null {
  const raw = body.year;
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== "number" || !Number.isInteger(raw)) {
    errors.push({ field: "year", message: "year must be an integer" });
    return null;
  }
  if (raw < MIN_YEAR || raw > MAX_YEAR) {
    errors.push({ field: "year", message: `year must be between ${MIN_YEAR} and ${MAX_YEAR}` });
    return null;
  }
  return raw;
}

function validateIsbn(body: Record<string, unknown>, errors: ValidationError[]): string | null {
  const raw = body.isbn;
  if (raw === undefined || raw === null) return null;
  if (typeof raw !== "string") {
    errors.push({ field: "isbn", message: "isbn must be a string" });
    return null;
  }
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;
  if (!ISBN_PATTERN.test(trimmed)) {
    errors.push({ field: "isbn", message: "isbn must be a valid ISBN-10 or ISBN-13" });
    return null;
  }
  return trimmed;
}

/**
 * Validates a full book payload (used for POST and PUT). Title and author are
 * required; year and isbn are optional but must be well-formed when present.
 */
export function validateBookInput(body: unknown): ValidationResult {
  if (!isPlainObject(body)) {
    return { ok: false, errors: [{ field: "body", message: "request body must be a JSON object" }] };
  }

  const errors: ValidationError[] = [];
  const title = validateRequiredString(body, "title", errors);
  const author = validateRequiredString(body, "author", errors);
  const year = validateYear(body, errors);
  const isbn = validateIsbn(body, errors);

  if (errors.length > 0 || title === undefined || author === undefined) {
    return { ok: false, errors };
  }
  return { ok: true, value: { title, author, year, isbn } };
}

/** Parses a path id parameter into a positive integer, or returns null. */
export function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
