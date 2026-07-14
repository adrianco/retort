/**
 * Unit / Integration Tests
 *
 * Tests internal modules: validation, DB operations.
 */

import { validateBook, ValidationError } from '../src/validation';
import { createDb, clearAll, createBook, getBook, updateBook, deleteBook, COUNT_ALL, COUNT_BY_AUTHOR } from '../src/db';

describe('validateBook', () => {
  it('accepts a complete book', () => {
    const result = validateBook({ title: 'Title', author: 'Author', year: 2020, isbn: '123' });
    expect(result.valid).toBe(true);
  });

  it('rejects when title is empty', () => {
    const result = validateBook({ title: '', author: 'Author' });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('title is required');
  });

  it('rejects when author is empty', () => {
    const result = validateBook({ title: 'Title', author: '' });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('author is required');
  });

  it('rejects when title is undefined', () => {
    const result = validateBook({ author: 'Author' as any });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('title is required');
  });

  it('rejects when author is undefined', () => {
    const result = validateBook({ title: 'Title' as any });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('author is required');
  });
});

describe('DB layer', () => {
  let db: any;

  beforeEach(() => {
    db = createDb(':memory:');
  });

  describe('clearAll', () => {
    it('removes all books', async () => {
      await createBook(db, 'T', 'A', 2000, '111');
      await createBook(db, 'T2', 'A2', 2010, '222');
      await clearAll(db);
      const count = COUNT_ALL(db);
      expect(count).toBe(0);
    });
  });

  describe('createBook', () => {
    it('creates and returns a book with an ID', async () => {
      const book = await createBook(db, 'Dune', 'Frank Herbert', 1965, '978-0441172719');
      expect(book.id).toBeGreaterThan(0);
      expect(book.title).toBe('Dune');
    });

    it('returns unique IDs for different books', async () => {
      const b1 = await createBook(db, 'T1', 'A1', 2000, '1');
      const b2 = await createBook(db, 'T2', 'A2', 2010, '2');
      expect(b1.id).not.toEqual(b2.id);
    });
  });

  describe('COUNT_ALL', () => {
    it('returns 0 when empty', () => {
      expect(COUNT_ALL(db)).toBe(0);
    });

    it('returns the correct count', async () => {
      await createBook(db, 'T1', 'A1', 2000, '1');
      await createBook(db, 'T2', 'A2', 2010, '2');
      await createBook(db, 'T3', 'A1', 2020, '3');
      expect(COUNT_ALL(db)).toBe(3);
    });
  });

  describe('COUNT_BY_AUTHOR', () => {
    it('returns correct count for an author', async () => {
      await createBook(db, 'T1', 'A1', 2000, '1');
      await createBook(db, 'T2', 'A2', 2010, '2');
      await createBook(db, 'T3', 'A1', 2020, '3');
      expect(COUNT_BY_AUTHOR(db, 'A1')).toBe(2);
      expect(COUNT_BY_AUTHOR(db, 'A2')).toBe(1);
    });
  });

  describe('getBook', () => {
    it('returns the book for a valid ID', async () => {
      const book = await createBook(db, 'T1', 'A1', 2000, '1');
      const found = await getBook(db, book.id);
      expect(found).toMatchObject({ id: book.id, title: 'T1' });
    });

    it('returns null for a non-existent ID', async () => {
      const result = await getBook(db, 9999);
      expect(result).toBeNull();
    });
  });

  describe('updateBook', () => {
    it('updates and returns the book', async () => {
      const book = await createBook(db, 'Old', 'Author', 2000, '1');
      const updated = await updateBook(db, book.id, 'New', 'Updated Author', 2024, '999');
      expect(updated).toMatchObject({ id: book.id, title: 'New', author: 'Updated Author', year: 2024 });
    });

    it('returns null when ID does not exist', async () => {
      const result = await updateBook(db, 9999, 'T', 'A', 2020, '1');
      expect(result).toBeNull();
    });
  });

  describe('deleteBook', () => {
    it('deletes and returns the book', async () => {
      const book = await createBook(db, 'ToDelete', 'Author', 2000, '1');
      const deleted = await deleteBook(db, book.id);
      expect(deleted).toMatchObject({ id: book.id, title: 'ToDelete' });
      expect(COUNT_ALL(db)).toBe(0);
    });

    it('returns null when ID does not exist', async () => {
      const result = await deleteBook(db, 9999);
      expect(result).toBeNull();
    });
  });
});
