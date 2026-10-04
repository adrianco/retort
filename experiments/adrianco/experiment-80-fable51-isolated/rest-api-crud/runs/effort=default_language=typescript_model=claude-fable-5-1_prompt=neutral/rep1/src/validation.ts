import type { BookInput } from "./db.js";

export type ValidationResult =
  | { ok: true; value: BookInput }
  | { ok: false; errors: string[] };

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
  if (year !== undefined && year !== null && !(typeof year === "number" && Number.isSafeInteger(year))) {
    errors.push("year must be an integer");
  }
  if (isbn !== undefined && isbn !== null && typeof isbn !== "string") {
    errors.push("isbn must be a string");
  }

  if (errors.length > 0) return { ok: false, errors };
  return {
    ok: true,
    value: {
      title: (title as string).trim(),
      author: (author as string).trim(),
      year: (year as number | null | undefined) ?? null,
      isbn: (isbn as string | null | undefined) ?? null,
    },
  };
}
