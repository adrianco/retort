export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
  created_at: string;
  updated_at: string;
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
