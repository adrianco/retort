export interface Book {
  id?: number;
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}

export interface BookInput {
  title: string;
  author: string;
  year?: number;
  isbn?: string;
}
