import { describe, expect, it } from 'vitest';
import {
  validateBookPayload,
  MIN_YEAR,
  MAX_YEAR,
} from '../src/validation.js';

describe('validateBookPayload (full / POST)', () => {
  it('accepts a complete valid payload', () => {
    const { patch, errors } = validateBookPayload({
      title: '  The Test  ',
      author: 'Author',
      year: 2001,
      isbn: '978-0-14-044913-4',
    });
    expect(errors).toEqual([]);
    expect(patch).toEqual({
      title: 'The Test',
      author: 'Author',
      year: 2001,
      isbn: '978-0-14-044913-4',
    });
  });

  it('accepts a minimal payload (title + author only)', () => {
    const { patch, errors } = validateBookPayload({ title: 'T', author: 'A' });
    expect(errors).toEqual([]);
    expect(patch).toEqual({ title: 'T', author: 'A' });
  });

  it('accepts a valid ISBN-10 with trailing X', () => {
    const { errors } = validateBookPayload({
      title: 'T',
      author: 'A',
      isbn: '0-8044-2957-X',
    });
    expect(errors).toEqual([]);
  });

  it('reports missing title and author together', () => {
    const { patch, errors } = validateBookPayload({ year: 1999 });
    expect(patch).toBeNull();
    expect(errors).toEqual(['title is required', 'author is required']);
  });

  it('rejects non-string title/author', () => {
    const { errors } = validateBookPayload({ title: 42, author: null });
    expect(errors).toEqual([
      'title must be a non-empty string',
      'author must be a non-empty string',
    ]);
  });

  it('rejects out-of-range years', () => {
    expect(validateBookPayload({ title: 'T', author: 'A', year: MIN_YEAR - 1 }).errors)
      .toEqual([`year must be an integer between ${MIN_YEAR} and ${MAX_YEAR}`]);
    expect(validateBookPayload({ title: 'T', author: 'A', year: MAX_YEAR + 1 }).errors)
      .toEqual([`year must be an integer between ${MIN_YEAR} and ${MAX_YEAR}`]);
  });

  it('rejects fractional years', () => {
    expect(validateBookPayload({ title: 'T', author: 'A', year: 1999.5 }).errors)
      .toHaveLength(1);
  });

  it('rejects invalid ISBN lengths', () => {
    expect(validateBookPayload({ title: 'T', author: 'A', isbn: '123' }).errors)
      .toEqual(['isbn must be a valid ISBN-10 or ISBN-13']);
  });

  it('rejects non-object bodies', () => {
    expect(validateBookPayload(null).errors).toEqual(['Request body must be a JSON object']);
    expect(validateBookPayload([1, 2]).errors).toEqual([
      'Request body must be a JSON object',
    ]);
    expect(validateBookPayload('str').errors).toEqual([
      'Request body must be a JSON object',
    ]);
  });
});

describe('validateBookPayload (partial / PUT)', () => {
  it('accepts a single-field update', () => {
    const { patch, errors } = validateBookPayload({ title: 'New' }, { partial: true });
    expect(errors).toEqual([]);
    expect(patch).toEqual({ title: 'New' });
  });

  it('accepts explicit nulls for optional fields', () => {
    const { patch, errors } = validateBookPayload(
      { year: null, isbn: null },
      { partial: true },
    );
    expect(errors).toEqual([]);
    expect(patch).toEqual({ year: null, isbn: null });
  });

  it('rejects an empty body', () => {
    const { patch, errors } = validateBookPayload({}, { partial: true });
    expect(patch).toBeNull();
    expect(errors).toEqual(['provide at least one of: title, author, year, isbn']);
  });

  it('still validates field values in partial mode', () => {
    const { errors } = validateBookPayload({ year: 'soon' }, { partial: true });
    expect(errors).toHaveLength(1);
  });
});
