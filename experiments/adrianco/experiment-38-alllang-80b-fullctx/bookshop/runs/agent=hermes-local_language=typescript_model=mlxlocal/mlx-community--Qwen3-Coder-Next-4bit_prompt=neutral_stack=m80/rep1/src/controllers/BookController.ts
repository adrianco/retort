import { Router, Request, Response, NextFunction } from 'express';
import { BookService } from '../services/BookService';
import { validateCreateBook, validateUpdateBook } from '../middleware/validation';

export class BookController {
  private router: Router;
  private bookService: BookService;

  constructor(bookService: BookService) {
    this.bookService = bookService;
    this.router = Router();
    this.setupRoutes();
  }

  private setupRoutes(): void {
    this.router.get('/', this.getAllBooks.bind(this));
    this.router.post('/', validateCreateBook, this.createBook.bind(this));
    this.router.get('/:id', this.getBookById.bind(this));
    this.router.put('/:id', validateUpdateBook, this.updateBook.bind(this));
    this.router.delete('/:id', this.deleteBook.bind(this));
  }

  public getRouter(): Router {
    return this.router;
  }

  private async getAllBooks(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const authorFilter = req.query.author as string | undefined;
      const books = await this.bookService.getBooks(authorFilter);
      res.json({ books });
    } catch (error) {
      next(error);
    }
  }

  private async createBook(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const input = req.body;
      const book = await this.bookService.createBook(input);
      res.status(201).json({ book });
    } catch (error) {
      next(error);
    }
  }

  private async getBookById(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      const book = await this.bookService.getBookById(id);
      
      if (!book) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }
      
      res.json({ book });
    } catch (error) {
      next(error);
    }
  }

  private async updateBook(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      const input = req.body;
      const book = await this.bookService.updateBook(id, input);
      
      if (!book) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }
      
      res.json({ book });
    } catch (error) {
      next(error);
    }
  }

  private async deleteBook(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await this.bookService.deleteBook(id);
      
      if (!deleted) {
        res.status(404).json({ error: 'Book not found' });
        return;
      }
      
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  }
}
