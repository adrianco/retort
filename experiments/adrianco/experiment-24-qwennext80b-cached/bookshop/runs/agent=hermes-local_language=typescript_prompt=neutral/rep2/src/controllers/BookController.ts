import { Request, Response } from 'express';
import { bookRepository } from '../database/BookRepository';
import { Book } from '../models/Book';

export class BookController {
  static getAll(req: Request, res: Response): void {
    const { author } = req.query;
    
    if (author && typeof author === 'string') {
      const books = bookRepository.getByAuthor(author);
      res.json(books);
      return;
    }

    const books = bookRepository.getAll();
    res.json(books);
  }

  static getById(req: Request, res: Response): void {
    const { id } = req.params;
    const book = bookRepository.getById(parseInt(id, 10));

    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.json(book);
  }

  static create(req: Request, res: Response): void {
    const book = bookRepository.create(req.body);
    res.status(201).json(book);
  }

  static update(req: Request, res: Response): void {
    const { id } = req.params;
    const book = bookRepository.update(parseInt(id, 10), req.body);

    if (!book) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.json(book);
  }

  static delete(req: Request, res: Response): void {
    const { id } = req.params;
    const deleted = bookRepository.delete(parseInt(id, 10));

    if (!deleted) {
      res.status(404).json({ error: 'Book not found' });
      return;
    }

    res.status(204).send();
  }
}
