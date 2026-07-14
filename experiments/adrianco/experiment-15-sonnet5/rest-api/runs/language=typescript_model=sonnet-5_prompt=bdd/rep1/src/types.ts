export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export interface BookInput {
  title?: unknown;
  author?: unknown;
  year?: unknown;
  isbn?: unknown;
}
