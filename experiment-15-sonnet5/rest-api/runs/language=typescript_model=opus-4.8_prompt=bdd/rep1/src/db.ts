import { createRequire } from "node:module";
import type { DatabaseSync } from "node:sqlite";

// Load the runtime value via createRequire so bundlers (e.g. Vite/Vitest)
// don't try to pre-resolve the `node:sqlite` builtin during transform.
// The `import type` above is erased at compile time, so it carries no runtime cost.
const require = createRequire(import.meta.url);
const { DatabaseSync: DatabaseSyncCtor } = require("node:sqlite") as {
  DatabaseSync: new (filename: string) => DatabaseSync;
};

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

export type BookInput = {
  title: string;
  author: string;
  year?: number | null;
  isbn?: string | null;
};

/**
 * Create a SQLite-backed database with the books schema applied.
 * Uses Node's built-in `node:sqlite` (an embedded DB — no native build step).
 * Pass ":memory:" for an ephemeral in-memory DB (used by tests).
 */
export function createDatabase(filename: string = "books.db"): DatabaseSync {
  const db = new DatabaseSyncCtor(filename);
  db.exec(`
    CREATE TABLE IF NOT EXISTS books (
      id     INTEGER PRIMARY KEY AUTOINCREMENT,
      title  TEXT NOT NULL,
      author TEXT NOT NULL,
      year   INTEGER,
      isbn   TEXT
    );
  `);
  return db;
}
