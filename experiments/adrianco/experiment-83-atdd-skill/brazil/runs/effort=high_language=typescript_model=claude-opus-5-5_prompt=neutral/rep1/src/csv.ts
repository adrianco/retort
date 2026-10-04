/**
 * Minimal RFC 4180 CSV parser.
 *
 * Handles quoted fields (including embedded commas, newlines and doubled
 * quotes), CRLF/LF line endings and a leading UTF-8 byte-order mark. The
 * datasets are small enough (largest ~9 MB) that parsing the whole file into
 * memory is fast and keeps the code simple.
 */
import { readFileSync } from "node:fs";

export type CsvRow = Record<string, string>;

export function parseCsv(text: string): string[][] {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let i = 0;
  const n = text.length;

  while (i < n) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i++;
        continue;
      }
      field += ch;
      i++;
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
      i++;
    } else if (ch === ",") {
      row.push(field);
      field = "";
      i++;
    } else if (ch === "\n" || ch === "\r") {
      row.push(field);
      field = "";
      rows.push(row);
      row = [];
      if (ch === "\r" && text[i + 1] === "\n") i++;
      i++;
    } else {
      field += ch;
      i++;
    }
  }
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  // Drop blank lines.
  return rows.filter((r) => !(r.length === 1 && r[0].trim() === ""));
}

/** Parse CSV text into objects keyed by the header row. */
export function parseCsvObjects(text: string): CsvRow[] {
  const rows = parseCsv(text);
  if (rows.length === 0) return [];
  const header = rows[0].map((h) => h.trim());
  const out: CsvRow[] = [];
  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r];
    const obj: CsvRow = {};
    for (let c = 0; c < header.length; c++) obj[header[c]] = cells[c] ?? "";
    out.push(obj);
  }
  return out;
}

export function readCsvFile(path: string): CsvRow[] {
  return parseCsvObjects(readFileSync(path, "utf8"));
}
