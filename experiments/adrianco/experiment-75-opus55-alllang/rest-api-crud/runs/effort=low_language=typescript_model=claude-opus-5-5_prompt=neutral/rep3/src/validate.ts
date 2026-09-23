import type { BookInput } from "./db.js";

export type ValidationResult = { ok: true; value: BookInput } | { ok: false; errors: string[] };

export function validateBook(body: unknown): ValidationResult {
  const errors: string[] = [];
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return { ok: false, errors: ["body must be a JSON object"] };
  }
  const b = body as Record<string, unknown>;
  const str = (v: unknown) => typeof v === "string" && v.trim().length > 0;
  if (!str(b.title)) errors.push("title is required and must be a non-empty string");
  if (!str(b.author)) errors.push("author is required and must be a non-empty string");
  if (b.year !== undefined && b.year !== null && !Number.isInteger(b.year)) errors.push("year must be an integer");
  if (b.isbn !== undefined && b.isbn !== null && typeof b.isbn !== "string") errors.push("isbn must be a string");
  if (errors.length) return { ok: false, errors };
  return {
    ok: true,
    value: {
      title: (b.title as string).trim(),
      author: (b.author as string).trim(),
      year: (b.year as number | undefined) ?? null,
      isbn: (b.isbn as string | undefined) ?? null,
    },
  };
}
