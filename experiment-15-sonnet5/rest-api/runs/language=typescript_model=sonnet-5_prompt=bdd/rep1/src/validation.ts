import { BookInput } from "./types";

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateBookInput(input: BookInput, opts: { partial?: boolean } = {}): ValidationResult {
  const errors: string[] = [];
  const { partial = false } = opts;

  const hasTitle = Object.prototype.hasOwnProperty.call(input, "title");
  const hasAuthor = Object.prototype.hasOwnProperty.call(input, "author");

  if (!partial || hasTitle) {
    if (typeof input.title !== "string" || input.title.trim().length === 0) {
      errors.push("title is required and must be a non-empty string");
    }
  }

  if (!partial || hasAuthor) {
    if (typeof input.author !== "string" || input.author.trim().length === 0) {
      errors.push("author is required and must be a non-empty string");
    }
  }

  if (input.year !== undefined && input.year !== null) {
    if (typeof input.year !== "number" || !Number.isInteger(input.year)) {
      errors.push("year must be an integer");
    }
  }

  if (input.isbn !== undefined && input.isbn !== null) {
    if (typeof input.isbn !== "string") {
      errors.push("isbn must be a string");
    }
  }

  return { valid: errors.length === 0, errors };
}
