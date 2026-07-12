import { jest } from '@jest/globals';

const mockDb = {
  exec: jest.fn(),
  all: jest.fn(),
  get: jest.fn(),
  run: jest.fn(),
  close: jest.fn(),
};

export const db = {
  connection: mockDb,
};

export const bookRepository = {
  getAll: jest.fn(),
  getById: jest.fn(),
  getByAuthor: jest.fn(),
  create: jest.fn(),
  update: jest.fn(),
  delete: jest.fn(),
};

export const DatabaseManager = jest.fn();
export default mockDb;
