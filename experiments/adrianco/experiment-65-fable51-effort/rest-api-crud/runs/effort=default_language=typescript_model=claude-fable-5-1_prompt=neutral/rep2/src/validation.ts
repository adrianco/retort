import { z } from "zod";

const currentYear = new Date().getUTCFullYear();

const trimmedRequired = (field: string) =>
  z
    .string({ required_error: `${field} is required`, invalid_type_error: `${field} must be a string` })
    .trim()
    .min(1, `${field} is required`)
    .max(500, `${field} must be at most 500 characters`);

const yearSchema = z
  .number({ invalid_type_error: "year must be an integer" })
  .int("year must be an integer")
  .min(-3000, "year is out of range")
  .max(currentYear + 5, "year is out of range");

// Accept ISBN-10 or ISBN-13, allowing hyphens/spaces; normalise to bare digits (X allowed as ISBN-10 check digit).
const isbnSchema = z
  .string({ invalid_type_error: "isbn must be a string" })
  .trim()
  .transform((s) => s.replace(/[-\s]/g, "").toUpperCase())
  .refine((s) => /^(\d{9}[\dX]|\d{13})$/.test(s), "isbn must be a valid ISBN-10 or ISBN-13");

export const createBookSchema = z
  .object({
    title: trimmedRequired("title"),
    author: trimmedRequired("author"),
    year: yearSchema.nullish(),
    isbn: isbnSchema.nullish(),
  })
  .strict();

export type CreateBookInput = z.infer<typeof createBookSchema>;

/** PUT semantics: full replacement, so title and author are required again. */
export const updateBookSchema = createBookSchema;
export type UpdateBookInput = z.infer<typeof updateBookSchema>;

export const idParamSchema = z.coerce
  .number({ invalid_type_error: "id must be a positive integer" })
  .int("id must be a positive integer")
  .positive("id must be a positive integer");

export const listQuerySchema = z
  .object({
    author: z.string().trim().min(1).optional(),
  })
  .passthrough();

export function formatZodError(error: z.ZodError): { field: string; message: string }[] {
  return error.issues.map((issue) => ({
    field: issue.path.length ? issue.path.join(".") : "(body)",
    message: issue.message,
  }));
}
