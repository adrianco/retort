/**
 * Minimal RFC 4180 CSV parser.
 *
 * Handles quoted fields (including embedded commas, quotes, and newlines),
 * a UTF-8 BOM on the first line, and both \n and \r\n line endings.
 */

export interface CsvTable {
  headers: string[];
  rows: Record<string, string>[];
}

export function parseCsv(text: string): CsvTable {
  // Strip UTF-8 BOM if present.
  if (text.charCodeAt(0) === 0xfeff) {
    text = text.slice(1);
  }

  const records: string[][] = [];
  let field = "";
  let record: string[] = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
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
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      record.push(field);
      field = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      record.push(field);
      field = "";
      records.push(record);
      record = [];
    } else {
      field += ch;
    }
  }
  // Flush final record if the file does not end with a newline.
  if (field.length > 0 || record.length > 0) {
    record.push(field);
    records.push(record);
  }

  if (records.length === 0) return { headers: [], rows: [] };

  const headers = records[0].map((h) => h.trim());
  const rows: Record<string, string>[] = [];
  for (let r = 1; r < records.length; r++) {
    const rec = records[r];
    // Skip blank lines.
    if (rec.length === 1 && rec[0].trim() === "") continue;
    const row: Record<string, string> = {};
    for (let c = 0; c < headers.length; c++) {
      row[headers[c]] = (rec[c] ?? "").trim();
    }
    rows.push(row);
  }
  return { headers, rows };
}
