/*
 * Context: CSV loading for the Kaggle files. Reads UTF-8 (Portuguese accents and
 * cedillas), strips the BOM that some exports (fifa_data.csv) begin with, and returns
 * header-keyed row objects. Numeric helpers return null for blank/invalid cells so
 * unplayed fixtures (empty scores) can be skipped cleanly.
 * Related: dataset.ts (consumer).
 */
import { readFileSync } from 'node:fs';
import { parse } from 'csv-parse/sync';

export type CsvRow = Record<string, string>;

export function readCsv(path: string): CsvRow[] {
  const text = readFileSync(path, { encoding: 'utf8' }).replace(/^﻿/, '');
  return parse(text, {
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
    trim: true,
  }) as CsvRow[];
}

/** Parse a numeric cell; returns null for blank or non-numeric values (e.g. "1.0" -> 1). */
export function toNumber(raw: string | undefined): number | null {
  if (raw === undefined) return null;
  const trimmed = raw.trim();
  if (trimmed === '') return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

/** Parse an integer-ish cell, tolerating FIFA-style "88+2" by taking the leading number. */
export function toLeadingInt(raw: string | undefined): number | null {
  if (raw === undefined) return null;
  const m = /^\s*(-?\d+)/.exec(raw);
  return m ? Number(m[1]) : null;
}
