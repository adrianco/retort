import { describe, it, expect } from '@jest/globals';
import { validateBookInput } from '../src/middleware/validation';
import { Request, Response } from 'express';

describe('Validation Middleware', () => {
  it('should return 400 if title is missing', () => {
    const req = {
      body: { author: 'Some Author' },
      query: {}
    } as Request;

    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    } as unknown as Response;

    const next = jest.fn();

    validateBookInput(req, res as Response, next);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({ error: 'Title is required' });
    expect(next).not.toHaveBeenCalled();
  });

  it('should return 400 if author is missing', () => {
    const req = {
      body: { title: 'Some Title' },
      query: {}
    } as Request;

    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    } as unknown as Response;

    const next = jest.fn();

    validateBookInput(req, res as Response, next);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({ error: 'Author is required' });
    expect(next).not.toHaveBeenCalled();
  });

  it('should call next if title and author are provided', () => {
    const req = {
      body: { title: 'Some Title', author: 'Some Author', year: 2024, isbn: '123' },
      query: {}
    } as Request;

    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    } as unknown as Response;

    const next = jest.fn();

    validateBookInput(req, res as Response, next);

    expect(next).toHaveBeenCalled();
    expect(res.status).not.toHaveBeenCalled();
  });

  it('should validate year if provided', () => {
    const req = {
      body: { title: 'Some Title', author: 'Some Author', year: -1 },
      query: {}
    } as Request;

    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    } as unknown as Response;

    const next = jest.fn();

    validateBookInput(req, res as Response, next);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({ error: 'Invalid year' });
  });

  it('should accept valid year', () => {
    const req = {
      body: { title: 'Some Title', author: 'Some Author', year: 2024 },
      query: {}
    } as Request;

    const res = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn()
    } as unknown as Response;

    const next = jest.fn();

    validateBookInput(req, res as Response, next);

    expect(next).toHaveBeenCalled();
  });
});
