export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface CreateBookInput {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface UpdateBookInput {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export function validateCreateBook(input: Partial<CreateBookInput>): string[] {
  const errors: string[] = [];

  if (!input.title || input.title.trim() === '') {
    errors.push('Title is required');
  }
  if (!input.author || input.author.trim() === '') {
    errors.push('Author is required');
  }
  if (input.year === undefined || input.year === null || isNaN(input.year) || input.year < 0 || input.year > 9999) {
    errors.push('Year is required and must be a valid number between 0 and 9999');
  }
  if (!input.isbn || input.isbn.trim() === '') {
    errors.push('ISBN is required');
  }

  return errors;
}

export function validateUpdateBook(input: Partial<UpdateBookInput>): string[] {
  const errors: string[] = [];

  if (input.title !== undefined && input.title.trim() === '') {
    errors.push('Title cannot be empty');
  }
  if (input.author !== undefined && input.author.trim() === '') {
    errors.push('Author cannot be empty');
  }
  if (input.year !== undefined && (isNaN(input.year) || input.year < 0 || input.year > 9999)) {
    errors.push('Year must be a valid number between 0 and 9999');
  }

  return errors;
}
