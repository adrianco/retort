import { describe, expect, it } from 'vitest';
import { parseCsv, parseCsvRecords } from '../../src/util/csv.js';

describe('parseCsv', () => {
  it('splits a plain table', () => {
    const { header, rows } = parseCsv('a,b,c\n1,2,3\n4,5,6\n');
    expect(header).toEqual(['a', 'b', 'c']);
    expect(rows).toEqual([
      ['1', '2', '3'],
      ['4', '5', '6'],
    ]);
  });

  it('keeps commas inside quoted fields', () => {
    const { rows } = parseCsv('a,b\n"Boavista Sport Club (antigo, Barreira) - RJ",2\n');
    expect(rows[0]).toEqual(['Boavista Sport Club (antigo, Barreira) - RJ', '2']);
  });

  it('unescapes doubled quotes', () => {
    const { rows } = parseCsv('a\n"He said ""hi"""\n');
    expect(rows[0]).toEqual(['He said "hi"']);
  });

  it('handles CRLF line endings and a missing final newline', () => {
    const { header, rows } = parseCsv('a,b\r\n1,2\r\n3,4');
    expect(header).toEqual(['a', 'b']);
    expect(rows).toEqual([
      ['1', '2'],
      ['3', '4'],
    ]);
  });

  it('strips a UTF-8 byte order mark from the first column name', () => {
    const { header } = parseCsv('﻿id,name\n1,x\n');
    expect(header[0]).toBe('id');
  });

  it('preserves accented characters', () => {
    const { rows } = parseCsv('team\nGrêmio\nAvaí\nSão Paulo\n');
    expect(rows.map((r) => r[0])).toEqual(['Grêmio', 'Avaí', 'São Paulo']);
  });

  it('ignores blank lines', () => {
    const { rows } = parseCsv('a\n1\n\n2\n\n');
    expect(rows).toEqual([['1'], ['2']]);
  });
});

describe('parseCsvRecords', () => {
  it('keys values by column name', () => {
    const records = parseCsvRecords('home,away\nFlamengo,Vasco\n');
    expect(records).toEqual([{ home: 'Flamengo', away: 'Vasco' }]);
  });

  it('fills missing trailing columns with empty strings', () => {
    const records = parseCsvRecords('a,b,c\n1,2\n');
    expect(records[0]).toEqual({ a: '1', b: '2', c: '' });
  });
});
