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

export function validateBookInput(body: unknown): ValidationResult {
  const errors: string[] = [];

  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return { ok: false, errors: ["request body must be a JSON object"] };
  }

  const { title, author, year, isbn } = body as Record<string, unknown>;

  if (typeof title !== "string" || title.trim() === "") {
    errors.push("title is required and must be a non-empty string");
  }
  if (typeof author !== "string" || author.trim() === "") {
    errors.push("author is required and must be a non-empty string");
  }
  if (year !== undefined && year !== null && !Number.isInteger(year)) {
    errors.push("year must be an integer if provided");
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string if provided");
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    errors: [],
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: (year as number | undefined) ?? null,
      isbn: (isbn as string | undefined) ?? null,
    },
  };
}
