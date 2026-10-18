import { describe, expect, it } from 'vitest';
import { parseCsv, parseCsvRecords } from '../src/csv.js';

describe('Feature: CSV parsing', () => {
  describe('Scenario: quoted fields with commas, escaped quotes and newlines', () => {
    it('Given a quoted field containing a comma, then it stays one cell', () => {
      expect(parseCsv('a,"b,c",d')).toEqual([['a', 'b,c', 'd']]);
    });

    it('Given doubled quotes, then they unescape to one quote', () => {
      expect(parseCsv('"say ""hi""",x')).toEqual([['say "hi"', 'x']]);
    });

    it('Given an embedded newline in quotes, then the row is not split', () => {
      expect(parseCsv('"line1\nline2",z\n')).toEqual([['line1\nline2', 'z']]);
    });
  });

  describe('Scenario: Windows line endings and a UTF-8 BOM', () => {
    it('Given CRLF rows with a BOM, then headers and values parse cleanly', () => {
      const records = parseCsvRecords('﻿ID,Name\r\n1,São Paulo\r\n2,Grêmio\r\n');
      expect(records).toEqual([
        { ID: '1', Name: 'São Paulo' },
        { ID: '2', Name: 'Grêmio' },
      ]);
    });
  });

  it('Given a short row, then missing cells become empty strings', () => {
    expect(parseCsvRecords('a,b,c\n1,2\n')).toEqual([{ a: '1', b: '2', c: '' }]);
  });
});
