import { Request, Response, NextFunction } from 'express';
import { DatabaseService } from '../database';

export interface Book {
  id: string;
  title: string;
  author: string;
  year: number;
  isbn: string;
  createdAt: string;
  updatedAt: string;
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

export class BookService {
  private database: DatabaseService;

  constructor(database: DatabaseService) {
    this.database = database;
  }

  async getBooks(authorFilter?: string): Promise<Book[]> {
    return this.database.getAllBooks(authorFilter);
  }

  async getBookById(id: string): Promise<Book | null> {
    return this.database.getBookById(id);
  }

  async createBook(input: CreateBookInput): Promise<Book> {
    // Validation is done by middleware
    return this.database.createBook(input);
  }

  async updateBook(id: string, input: UpdateBookInput): Promise<Book | null> {
    // Validation is done by middleware
    return this.database.updateBook(id, input);
  }

  async deleteBook(id: string): Promise<boolean> {
    return this.database.deleteBook(id);
  }
}
