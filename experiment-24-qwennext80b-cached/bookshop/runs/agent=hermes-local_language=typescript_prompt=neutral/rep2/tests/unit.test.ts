import { validateBookInput, validateBookUpdate } from '../src/models/Book';

describe('Book Model Validation', () => {
  describe('validateBookInput', () => {
    it('should validate correct book input', () => {
      const result = validateBookInput({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890',
      });

      expect(result.valid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('should reject empty title', () => {
      const result = validateBookInput({
        title: '',
        author: 'Test Author',
        year: 2023,
        isbn: '1234567890',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Title is required and must be a non-empty string');
    });

    it('should reject empty author', () => {
      const result = validateBookInput({
        title: 'Test Book',
        author: '',
        year: 2023,
        isbn: '1234567890',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Author is required and must be a non-empty string');
    });

    it('should reject invalid year', () => {
      const result = validateBookInput({
        title: 'Test Book',
        author: 'Test Author',
        year: -1,
        isbn: '1234567890',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Year must be a valid integer');
    });

    it('should reject invalid year (not integer)', () => {
      const result = validateBookInput({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023.5,
        isbn: '1234567890',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Year must be a valid integer');
    });

    it('should reject empty ISBN', () => {
      const result = validateBookInput({
        title: 'Test Book',
        author: 'Test Author',
        year: 2023,
        isbn: '',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('ISBN is required and must be a non-empty string');
    });

    it('should reject non-object input (null)', () => {
      const result = validateBookInput(null);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should reject non-object input (array)', () => {
      const result = validateBookInput([]);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('validateBookUpdate', () => {
    it('should validate partial update', () => {
      const result = validateBookUpdate({
        title: 'Updated Title',
      });

      expect(result.valid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('should allow empty update object', () => {
      const result = validateBookUpdate({});

      expect(result.valid).toBe(true);
      expect(result.errors).toEqual([]);
    });

    it('should reject invalid title in update', () => {
      const result = validateBookUpdate({
        title: '',
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Title must be a non-empty string');
    });

    it('should reject invalid year in update', () => {
      const result = validateBookUpdate({
        year: -1,
      });

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Year must be a valid integer');
    });
  });
});
