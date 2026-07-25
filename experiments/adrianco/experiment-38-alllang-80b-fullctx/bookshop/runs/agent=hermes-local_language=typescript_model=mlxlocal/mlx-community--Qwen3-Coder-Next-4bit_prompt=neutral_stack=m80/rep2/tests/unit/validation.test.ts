import { validateBookInput, validateBookUpdate } from '../src/middleware/validation';

describe('Validation Middleware', () => {
  let req: any;
  let res: any;
  let next: jest.Mock;

  beforeEach(() => {
    req = {};
    res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn(),
    };
    next = jest.fn();
  });

  describe('validateBookInput', () => {
    it('should pass validation when all fields are valid', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
        year: 2024,
        isbn: '1234567890',
      };

      validateBookInput(req, res as any, next);
      expect(next).toHaveBeenCalled();
    });

    it('should reject when title is missing', () => {
      req.body = {
        author: 'Test Author',
        year: 2024,
        isbn: '1234567890',
      };

      validateBookInput(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Title') })
      );
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject when author is missing', () => {
      req.body = {
        title: 'Test Book',
        year: 2024,
        isbn: '1234567890',
      };

      validateBookInput(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Author') })
      );
      expect(next).not.toHaveBeenCalled();
    });

    it('should reject when title is empty string', () => {
      req.body = {
        title: '',
        author: 'Test Author',
      };

      validateBookInput(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Title') })
      );
    });

    it('should reject when author is empty string', () => {
      req.body = {
        title: 'Test Book',
        author: '',
      };

      validateBookInput(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Author') })
      );
    });

    it('should reject when year is not a number', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
        year: 'not-a-number',
      };

      validateBookInput(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Year') })
      );
    });

    it('should accept year as optional', () => {
      req.body = {
        title: 'Test Book',
        author: 'Test Author',
      };

      validateBookInput(req, res as any, next);
      expect(next).toHaveBeenCalled();
    });
  });

  describe('validateBookUpdate', () => {
    it('should pass validation when all fields are valid', () => {
      req.body = {
        title: 'Updated Title',
        author: 'Updated Author',
        year: 2025,
        isbn: '0987654321',
      };

      validateBookUpdate(req, res as any, next);
      expect(next).toHaveBeenCalled();
    });

    it('should allow partial updates', () => {
      req.body = {
        title: 'Updated Title',
      };

      validateBookUpdate(req, res as any, next);
      expect(next).toHaveBeenCalled();
    });

    it('should reject when title is empty string', () => {
      req.body = {
        title: '',
      };

      validateBookUpdate(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Title') })
      );
    });

    it('should reject when author is empty string', () => {
      req.body = {
        author: '',
      };

      validateBookUpdate(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Author') })
      );
    });

    it('should reject when year is not a number', () => {
      req.body = {
        year: 'not-a-number',
      };

      validateBookUpdate(req, res as any, next);
      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith(
        expect.objectContaining({ error: expect.stringContaining('Year') })
      );
    });
  });
});
