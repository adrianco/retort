/*
 * Context: Feature tests for date parsing across ISO, Brazilian and timestamped formats.
 * Related: src/dates.ts.
 */
import { describe, expect, it } from 'vitest';
import { parseDate } from '../src/dates.js';

describe('Feature: Date parsing', () => {
  it('Scenario: ISO dates and timestamps are normalised to YYYY-MM-DD', () => {
    expect(parseDate('2023-09-24')).toBe('2023-09-24');
    expect(parseDate('2012-05-19 18:30:00')).toBe('2012-05-19');
  });

  it('Scenario: Brazilian DD/MM/YYYY dates are understood', () => {
    expect(parseDate('29/03/2003')).toBe('2003-03-29');
    expect(parseDate('7/4/2020')).toBe('2020-04-07');
  });

  it('Scenario: invalid or empty values return null', () => {
    expect(parseDate('')).toBeNull();
    expect(parseDate(undefined)).toBeNull();
    expect(parseDate('31/02/2020')).toBeNull();
    expect(parseDate('not a date')).toBeNull();
  });
});
