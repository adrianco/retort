export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] };

function requiredString(body: Record<string, unknown>, field: string, errors: string[]): string {
  const v = body[field];
  if (typeof v !== "string" || v.trim() === "") {
    errors.push(`${field} is required and must be a non-empty string`);
    return "";
  }
  return v.trim();
}

/** Validates a request body for creating or replacing a book. */
export function validateBook(body: unknown): ValidationResult {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { ok: false, errors: ["request body must be a JSON object"] };
  }
  const b = body as Record<string, unknown>;
  const errors: string[] = [];

  const title = requiredString(b, "title", errors);
  const author = requiredString(b, "author", errors);

  let year: number | null = null;
  if (b.year !== undefined && b.year !== null) {
    if (typeof b.year !== "number" || !Number.isInteger(b.year)) {
      errors.push("year must be an integer");
    } else {
      year = b.year;
    }
  }

  let isbn: string | null = null;
  if (b.isbn !== undefined && b.isbn !== null) {
    if (typeof b.isbn !== "string" || b.isbn.trim() === "") {
      errors.push("isbn must be a non-empty string");
    } else {
      isbn = b.isbn.trim();
    }
  }

  return errors.length > 0 ? { ok: false, errors } : { ok: true, value: { title, author, year, isbn } };
}
