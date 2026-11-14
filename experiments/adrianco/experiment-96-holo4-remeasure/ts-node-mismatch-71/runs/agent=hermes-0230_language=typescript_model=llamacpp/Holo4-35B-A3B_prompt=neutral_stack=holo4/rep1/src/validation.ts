export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export function validateCreateBook(title: string, author: string, year: number, isbn: string): ValidationResult {
  const errors: string[] = [];

  if (!title || title.trim() === '') {
    errors.push('title is required');
  }
  if (!author || author.trim() === '') {
    errors.push('author is required');
  }
  if (!Number.isInteger(year) || year < 0) {
    errors.push('year must be a positive integer');
  }
  if (!isbn || isbn.trim() === '') {
    errors.push('isbn is required');
  }

  return { valid: errors.length === 0, errors };
}

export function validateUpdateBook(updates: { title?: string; author?: string; year?: number; isbn?: string }): ValidationResult {
  const errors: string[] = [];

  if (updates.title !== undefined && (typeof updates.title !== 'string' || updates.title.trim() === '')) {
    errors.push('title must be a non-empty string');
  }
  if (updates.author !== undefined && (typeof updates.author !== 'string' || updates.author.trim() === '')) {
    errors.push('author must be a non-empty string');
  }
  if (updates.year !== undefined && (!Number.isInteger(updates.year) || updates.year < 0)) {
    errors.push('year must be a positive integer');
  }
  if (updates.isbn !== undefined && (typeof updates.isbn !== 'string' || updates.isbn.trim() === '')) {
    errors.push('isbn must be a non-empty string');
  }

  return { valid: errors.length === 0, errors };
}
