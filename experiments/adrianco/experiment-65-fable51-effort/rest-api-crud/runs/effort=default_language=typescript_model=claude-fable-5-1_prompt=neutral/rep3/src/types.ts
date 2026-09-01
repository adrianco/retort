export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface ValidationError {
  field: string;
  message: string;
}
