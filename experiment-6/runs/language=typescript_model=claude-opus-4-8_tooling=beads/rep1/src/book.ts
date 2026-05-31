import type { NewBook } from "./db.js";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  value?: NewBook;
}

/**
 * Validate and normalize an incoming book payload.
 * `title` and `author` are required, non-empty strings.
 * `year` (if present) must be an integer; `isbn` (if present) a string.
 */
export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { valid: false, errors: ["request body must be a JSON object"] };
  }

  const b = body as Record<string, unknown>;

  const title = typeof b.title === "string" ? b.title.trim() : "";
  if (!title) errors.push("title is required");

  const author = typeof b.author === "string" ? b.author.trim() : "";
  if (!author) errors.push("author is required");

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year === "number" && Number.isInteger(b.year)) {
      year = b.year;
    } else {
      errors.push("year must be an integer");
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn === "string") {
      isbn = b.isbn.trim() || null;
    } else {
      errors.push("isbn must be a string");
    }
  }

  if (errors.length > 0) return { valid: false, errors };

  return { valid: true, errors: [], value: { title, author, year, isbn } };
}
