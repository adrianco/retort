export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] };

function isBlank(value: unknown): boolean {
  return value === undefined || value === null || value === "";
}

// Validates a request body for creating or replacing a book.
export function validateBook(body: unknown): ValidationResult {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { ok: false, errors: ["request body must be a JSON object"] };
  }
  const { title, author, year, isbn } = body as Record<string, unknown>;
  const errors: string[] = [];

  if (typeof title !== "string" || title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof author !== "string" || author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }
  if (!isBlank(year) && (typeof year !== "number" || !Number.isInteger(year))) {
    errors.push("year must be an integer");
  }
  if (!isBlank(isbn) && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: isBlank(year) ? null : (year as number),
      isbn: isBlank(isbn) ? null : (isbn as string).trim(),
    },
  };
}
