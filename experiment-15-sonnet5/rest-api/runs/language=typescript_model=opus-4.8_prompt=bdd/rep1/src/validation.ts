import type { BookInput } from "./db.js";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  value?: BookInput;
}

/**
 * Validate and normalise a request body into a BookInput.
 * Rules: title and author are required non-empty strings.
 * year (if present) must be an integer; isbn (if present) must be a string.
 */
export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { valid: false, errors: ["Request body must be a JSON object"] };
  }

  const data = body as Record<string, unknown>;

  const title = typeof data.title === "string" ? data.title.trim() : "";
  const author = typeof data.author === "string" ? data.author.trim() : "";

  if (!title) {
    errors.push("title is required and must be a non-empty string");
  }
  if (!author) {
    errors.push("author is required and must be a non-empty string");
  }

  let year: number | null = null;
  if (data.year !== undefined && data.year !== null) {
    if (typeof data.year !== "number" || !Number.isInteger(data.year)) {
      errors.push("year must be an integer");
    } else {
      year = data.year;
    }
  }

  let isbn: string | null = null;
  if (data.isbn !== undefined && data.isbn !== null) {
    if (typeof data.isbn !== "string") {
      errors.push("isbn must be a string");
    } else {
      isbn = data.isbn.trim();
    }
  }

  if (errors.length > 0) {
    return { valid: false, errors };
  }

  return { valid: true, errors: [], value: { title, author, year, isbn } };
}
