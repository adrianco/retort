import { BookInput } from './types';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  data: {
    title?: string;
    author?: string;
    year: number | null;
    isbn: string | null;
  };
}

export function validateBookInput(body: BookInput, opts: { partial?: boolean } = {}): ValidationResult {
  const errors: string[] = [];
  const { partial = false } = opts;

  let title: string | undefined;
  if (body.title !== undefined) {
    if (typeof body.title !== 'string' || body.title.trim() === '') {
      errors.push('title must be a non-empty string');
    } else {
      title = body.title;
    }
  } else if (!partial) {
    errors.push('title is required');
  }

  let author: string | undefined;
  if (body.author !== undefined) {
    if (typeof body.author !== 'string' || body.author.trim() === '') {
      errors.push('author must be a non-empty string');
    } else {
      author = body.author;
    }
  } else if (!partial) {
    errors.push('author is required');
  }

  let year: number | null = null;
  if (body.year !== undefined && body.year !== null) {
    if (typeof body.year !== 'number' || !Number.isInteger(body.year)) {
      errors.push('year must be an integer');
    } else {
      year = body.year;
    }
  }

  let isbn: string | null = null;
  if (body.isbn !== undefined && body.isbn !== null) {
    if (typeof body.isbn !== 'string') {
      errors.push('isbn must be a string');
    } else {
      isbn = body.isbn;
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    data: { title, author, year, isbn },
  };
}
