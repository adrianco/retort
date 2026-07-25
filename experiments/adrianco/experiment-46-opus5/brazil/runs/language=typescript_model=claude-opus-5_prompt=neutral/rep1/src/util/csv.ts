/**
 * Minimal RFC 4180 CSV reader.
 *
 * The Kaggle files mix conventions -- some quote every field, some quote none,
 * one carries a UTF-8 BOM, and several contain commas and accented characters
 * inside quoted values (e.g. `"Boavista Sport Club (antigo ...) - RJ"`). Rather
 * than take a dependency we parse the handful of cases that actually occur:
 * quoted fields, doubled quotes as escapes, LF/CRLF line endings.
 */

export interface CsvTable {
  header: string[];
  rows: string[][];
}

const BOM = '﻿';

/** Split raw CSV text into a header row plus data rows. */
export function parseCsv(input: string): CsvTable {
  const text = input.startsWith(BOM) ? input.slice(BOM.length) : input;
  const rows: string[][] = [];

  let field = '';
  let row: string[] = [];
  let inQuotes = false;
  let sawAnyChar = false;

  const endField = () => {
    row.push(field);
    field = '';
  };
  const endRow = () => {
    endField();
    // Ignore blank trailing lines, but keep genuinely empty in-file rows out too:
    // a row of one empty field carries no data in any of our sources.
    if (!(row.length === 1 && row[0] === '')) rows.push(row);
    row = [];
    sawAnyChar = false;
  };

  for (let i = 0; i < text.length; i++) {
    const ch = text[i]!;

    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }

    switch (ch) {
      case '"':
        // A quote only opens a quoted section at the start of a field; a stray
        // mid-field quote is kept verbatim.
        if (field === '' && !sawAnyChar) inQuotes = true;
        else field += ch;
        sawAnyChar = true;
        break;
      case ',':
        endField();
        sawAnyChar = false;
        break;
      case '\r':
        break;
      case '\n':
        endRow();
        break;
      default:
        field += ch;
        sawAnyChar = true;
    }
  }

  // Flush whatever the final line left behind (files may not end with a newline).
  if (field !== '' || row.length > 0) endRow();

  const header = rows.shift() ?? [];
  return { header: header.map((h) => h.trim()), rows };
}

/**
 * Parse into record objects keyed by column name.
 *
 * Short rows yield `''` for missing columns rather than `undefined`, so callers
 * can treat every column as a string.
 */
export function parseCsvRecords(input: string): Array<Record<string, string>> {
  const { header, rows } = parseCsv(input);
  return rows.map((row) => {
    const record: Record<string, string> = {};
    for (let i = 0; i < header.length; i++) record[header[i]!] = row[i] ?? '';
    return record;
  });
}
