/**
 * Thin synchronous CSV loader used by the data store.
 *
 * Wraps csv-parse with the options the Kaggle files need: BOM stripping (the
 * FIFA export starts with a UTF-8 BOM), quoted-field handling, and UTF-8
 * decoding for accented Portuguese team names.
 */
import { readFileSync } from "node:fs";
import { parse } from "csv-parse/sync";

export type CsvRow = Record<string, string>;

/** Read and parse a CSV file into an array of column-keyed row objects. */
export function loadCsv(filePath: string): CsvRow[] {
  const raw = readFileSync(filePath, "utf8");
  return parse(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_column_count: true,
    trim: true,
  }) as CsvRow[];
}
