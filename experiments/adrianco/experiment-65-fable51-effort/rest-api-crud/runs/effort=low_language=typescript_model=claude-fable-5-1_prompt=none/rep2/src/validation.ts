export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  value?: BookInput;
}

const CURRENT_YEAR_MAX = new Date().getFullYear() + 5;

export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return { ok: false, errors: ["request body must be a JSON object"] };
  }
  const b = body as Record<string, unknown>;

  const title = typeof b.title === "string" ? b.title.trim() : "";
  if (!title) errors.push("title is required and must be a non-empty string");

  const author = typeof b.author === "string" ? b.author.trim() : "";
  if (!author) errors.push("author is required and must be a non-empty string");

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== "number" || !Number.isInteger(b.year) || b.year < 0 || b.year > CURRENT_YEAR_MAX) {
      errors.push(`year must be an integer between 0 and ${CURRENT_YEAR_MAX}`);
    } else {
      year = b.year;
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== "string") {
      errors.push("isbn must be a string");
    } else {
      const cleaned = b.isbn.replace(/[-\s]/g, "");
      if (!/^(\d{9}[\dXx]|\d{13})$/.test(cleaned)) {
        errors.push("isbn must be a valid ISBN-10 or ISBN-13");
      } else {
        isbn = b.isbn.trim();
      }
    }
  }

  if (errors.length) return { ok: false, errors };
  return { ok: true, errors: [], value: { title, author, year, isbn } };
}

export function parseId(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}
