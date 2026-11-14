export interface Book {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface CreateBookRequest {
  title: string;
  author: string;
  year: number;
  isbn: string;
}

export interface UpdateBookRequest {
  title?: string;
  author?: string;
  year?: number;
  isbn?: string;
}
