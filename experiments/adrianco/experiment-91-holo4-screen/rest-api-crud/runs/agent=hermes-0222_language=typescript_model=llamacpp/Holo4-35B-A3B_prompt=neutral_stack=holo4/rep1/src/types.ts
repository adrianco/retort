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

export interface ValidationError {
  field: string;
  message: string;
}
