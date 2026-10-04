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
  const value = body[field];
  if (typeof value !== "string" || value.trim() === "") {
    errors.push(`${field} is required and must be a non-empty string`);
    return "";
  }
  return value.trim();
}

export function validateBook(body: unknown): ValidationResult {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { ok: false, errors: ["request body must be a JSON object"] };
  }
  const input = body as Record<string, unknown>;
  const errors: string[] = [];

  const title = requiredString(input, "title", errors);
  const author = requiredString(input, "author", errors);

  let year: number | null = null;
  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== "number" || !Number.isInteger(input.year)) {
      errors.push("year must be an integer");
    } else {
      year = input.year;
    }
  }

  let isbn: string | null = null;
  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string" || input.isbn.trim() === "") {
      errors.push("isbn must be a non-empty string");
    } else {
      isbn = input.isbn.trim();
    }
  }

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, value: { title, author, year, isbn } };
}
