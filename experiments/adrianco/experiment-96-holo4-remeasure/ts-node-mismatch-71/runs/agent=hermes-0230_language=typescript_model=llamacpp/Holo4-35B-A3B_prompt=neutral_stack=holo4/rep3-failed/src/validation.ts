export interface BookInput {
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export function validateBook(input: Partial<BookInput>): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!input.title || input.title.trim() === '') {
    errors.push({ field: 'title', message: 'Title is required' });
  }

  if (!input.author || input.author.trim() === '') {
    errors.push({ field: 'author', message: 'Author is required' });
  }

  if (input.year !== undefined && (input.year < 0 || input.year > new Date().getFullYear() + 1)) {
    errors.push({ field: 'year', message: 'Year must be a valid year' });
  }

  return errors;
}
