export interface ValidationError {
  valid: boolean;
  error?: string;
}

export interface BookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export function validateBook(input: BookInput): ValidationError {
  if (!input.title || input.title.trim() === '') {
    return { valid: false, error: 'title is required' };
  }
  if (!input.author || input.author.trim() === '') {
    return { valid: false, error: 'author is required' };
  }
  return { valid: true };
}
