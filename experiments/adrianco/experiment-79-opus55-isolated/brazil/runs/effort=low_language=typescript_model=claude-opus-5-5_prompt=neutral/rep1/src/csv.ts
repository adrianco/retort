/** Minimal RFC 4180 CSV parser (quoted fields, embedded commas/newlines, BOM). */
export function parseCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text);
  const header = rows.shift();
  if (!header) return [];
  return rows
    .filter((r) => r.length > 1 || r[0] !== '')
    .map((r) => {
      const rec: Record<string, string> = {};
      header.forEach((h, i) => (rec[h] = r[i] ?? ''));
      return rec;
    });
}

export function parseRows(text: string): string[][] {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else quoted = false;
      } else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += c;
  }
  if (field !== '' || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}
