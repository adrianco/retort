/** A book as stored and returned by the API. */
export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** The validated, normalized payload used to create or replace a book. */
export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

/** A single field-level validation failure. */
export interface FieldError {
  field: string;
  message: string;
}
