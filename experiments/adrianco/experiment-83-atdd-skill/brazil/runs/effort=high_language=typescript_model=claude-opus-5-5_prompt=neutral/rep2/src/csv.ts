/**
 * Minimal RFC 4180 CSV parser.
 *
 * Handles quoted fields, escaped quotes (""), embedded commas/newlines,
 * CRLF line endings and a leading UTF-8 byte-order mark. Returns rows as
 * objects keyed by the header row.
 */

export type CsvRow = Record<string, string>;

export function parseCsvRows(text: string): string[][] {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  const n = text.length;

  for (let i = 0; i < n; i++) {
    const ch = text[i];
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
    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      rows.push(row);
      row = [];
    } else {
      field += ch;
    }
  }
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  // Drop blank lines.
  return rows.filter((r) => !(r.length === 1 && r[0] === ""));
}

export function parseCsv(text: string): CsvRow[] {
  const rows = parseCsvRows(text);
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
