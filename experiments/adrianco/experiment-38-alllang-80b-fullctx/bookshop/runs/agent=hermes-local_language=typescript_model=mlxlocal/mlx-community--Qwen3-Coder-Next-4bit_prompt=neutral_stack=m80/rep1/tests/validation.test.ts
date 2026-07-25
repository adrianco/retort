import { validateCreateBook, validateUpdateBook, CreateBookInput, UpdateBookInput } from '../src/middleware/validation';
import { Request, Response, NextFunction } from 'express';

describe('Validation Middleware Tests', () => {
  let req: Partial<Request>;
  let res: Partial<Response>;
  let next: jest.Mock;

  beforeEach(() => {
    req = {};
    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis()
    };
    next = jest.fn();
  });

  describe('validateCreateBook', () => {
    it('should call next when all fields are valid', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
        year: 2024,
        isbn: '123-4567890123'
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(next).toHaveBeenCalledTimes(1);
      expect(res.status).not.toHaveBeenCalled();
    });

    it('should return 400 when title is missing', () => {
      req.body = {
        author: 'Test Author',
        year: 2024,
        isbn: '123-4567890123'
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Title') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when author is missing', () => {
      req.body = {
        title: 'Test Book',
        year: 2024,
        isbn: '123-4567890123'
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Author') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when year is missing', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
        isbn: '123-4567890123'
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Year') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when isbn is missing', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
        year: 2024
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('ISBN') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when title is empty string', () => {
      req.body = {
        title: '',
        author: 'Test Author',
        year: 2024,
        isbn: '123-4567890123'
      };

      validateCreateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(next).not.toHaveBeenCalled();
    });
  });

  describe('validateUpdateBook', () => {
    it('should call next when at least one field is provided', () => {
      req.body = {
        title: 'Updated Title'
      };

      validateUpdateBook(req as Request, res as Response, next);

      expect(next).toHaveBeenCalledTimes(1);
      expect(res.status).not.toHaveBeenCalled();
    });

    it('should return 400 when no fields are provided', () => {
      req.body = {};

      validateUpdateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      const errorArg = (res.json as jest.Mock).mock.calls[0][0];
      expect(errorArg.error).toContain('at least one field');
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when title is empty string', () => {
      req.body = {
        title: ''
      };

      validateUpdateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Title') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when author is empty string', () => {
      req.body = {
        author: ''
      };

      validateUpdateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Author') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when year is null', () => {
      req.body = {
        year: null
      };

      validateUpdateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('Year') });
      expect(next).not.toHaveBeenCalled();
    });

    it('should return 400 when isbn is empty string', () => {
      req.body = {
        isbn: ''
      };

      validateUpdateBook(req as Request, res as Response, next);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({ error: expect.stringContaining('ISBN') });
      expect(next).not.toHaveBeenCalled();
    });
  });
});
