import { describe, expect, it } from 'vitest';
import { daysBetween, parseDate, parseDateBound } from '../../src/domain/dates.js';

describe('parseDate', () => {
  it('reads ISO dates', () => {
    expect(parseDate('2023-09-24')).toEqual({ date: '2023-09-24' });
  });

  it('reads ISO dates with a kick-off time', () => {
    expect(parseDate('2012-05-19 18:30:00')).toEqual({ date: '2012-05-19', time: '18:30' });
  });

  it('reads the Brazilian day-first format', () => {
    expect(parseDate('29/03/2003')).toEqual({ date: '2003-03-29' });
  });

  it('pads single-digit Brazilian days and months', () => {
    expect(parseDate('1/5/2010')).toEqual({ date: '2010-05-01' });
  });

  it('treats blank, NA and nan as missing', () => {
    expect(parseDate('')).toBeUndefined();
    expect(parseDate('NA')).toBeUndefined();
    expect(parseDate('nan')).toBeUndefined();
    expect(parseDate(undefined)).toBeUndefined();
  });

  it('rejects impossible calendar dates', () => {
    expect(parseDate('2023-02-30')).toBeUndefined();
    expect(parseDate('2023-13-01')).toBeUndefined();
    expect(parseDate('31/02/2020')).toBeUndefined();
  });

  it('accepts 29 February only in leap years', () => {
    expect(parseDate('2020-02-29')?.date).toBe('2020-02-29');
    expect(parseDate('2019-02-29')).toBeUndefined();
    expect(parseDate('1900-02-29')).toBeUndefined();
    expect(parseDate('2000-02-29')?.date).toBe('2000-02-29');
  });
});

describe('parseDateBound', () => {
  it('returns the normalised date', () => {
    expect(parseDateBound('29/03/2003', 'dateFrom')).toBe('2003-03-29');
  });

  it('throws with the label so the caller knows which argument was wrong', () => {
    expect(() => parseDateBound('yesterday', 'dateFrom')).toThrow(/dateFrom/);
  });
});

describe('daysBetween', () => {
  it('counts whole days regardless of order', () => {
    expect(daysBetween('2019-01-01', '2019-01-08')).toBe(7);
    expect(daysBetween('2019-01-08', '2019-01-01')).toBe(7);
  });

  it('is zero for the same day', () => {
    expect(daysBetween('2019-01-01', '2019-01-01')).toBe(0);
  });
});
