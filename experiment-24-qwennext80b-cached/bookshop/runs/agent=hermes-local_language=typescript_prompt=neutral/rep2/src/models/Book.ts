export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
  createdAt: string;
  updatedAt: string;
}

export interface BookInput {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}

export const validateBookInput = (data: unknown): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (typeof data !== 'object' || data === null) {
    errors.push('Request body must be an object');
    return { valid: false, errors };
  }

  const book = data as Partial<BookInput>;

  if (typeof book.title !== 'string' || book.title.trim().length === 0) {
    errors.push('Title is required and must be a non-empty string');
  }

  if (typeof book.author !== 'string' || book.author.trim().length === 0) {
    errors.push('Author is required and must be a non-empty string');
  }

  if (typeof book.year !== 'number' || !Number.isInteger(book.year) || book.year < 0) {
    errors.push('Year must be a valid integer');
  }

  if (typeof book.isbn !== 'string' || book.isbn.trim().length === 0) {
    errors.push('ISBN is required and must be a non-empty string');
  }

  return { valid: errors.length === 0, errors };
};

export const validateBookUpdate = (data: unknown): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (typeof data !== 'object' || data === null) {
    errors.push('Request body must be an object');
    return { valid: false, errors };
  }

  const book = data as Partial<BookUpdate>;

  if (book.title !== undefined) {
    if (typeof book.title !== 'string' || book.title.trim().length === 0) {
      errors.push('Title must be a non-empty string');
    }
  }

  if (book.author !== undefined) {
    if (typeof book.author !== 'string' || book.author.trim().length === 0) {
      errors.push('Author must be a non-empty string');
    }
  }

  if (book.year !== undefined) {
    if (typeof book.year !== 'number' || !Number.isInteger(book.year) || book.year < 0) {
      errors.push('Year must be a valid integer');
    }
  }

  if (book.isbn !== undefined) {
    if (typeof book.isbn !== 'string' || book.isbn.trim().length === 0) {
      errors.push('ISBN must be a non-empty string');
    }
  }

  return { valid: errors.length === 0, errors };
};
