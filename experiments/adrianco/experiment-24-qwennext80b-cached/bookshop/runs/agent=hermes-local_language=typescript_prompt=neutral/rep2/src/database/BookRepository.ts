import { Book, BookInput, BookUpdate } from '../models/Book';
import { db } from './Database';

export class BookRepository {
  getAll(): Book[] {
    return db.getAll();
  }

  getById(id: number): Book | undefined {
    return db.getById(id);
  }

  getByAuthor(author: string): Book[] {
    return db.getByAuthor(author);
  }

  create(book: BookInput): Book {
    return db.create(book);
  }

  update(id: number, book: BookUpdate): Book | undefined {
    return db.update(id, book);
  }

  delete(id: number): boolean {
    return db.delete(id);
  }
}

export const bookRepository = new BookRepository();
