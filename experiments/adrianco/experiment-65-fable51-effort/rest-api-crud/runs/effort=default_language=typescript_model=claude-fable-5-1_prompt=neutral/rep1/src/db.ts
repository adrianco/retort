import { DatabaseSync } from "node:sqlite";

export interface Book {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BookInput {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

const SCHEMA = `
  CREATE TABLE IF NOT EXISTS books (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    year       INTEGER,
    isbn       TEXT,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  );
  CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books (isbn) WHERE isbn IS NOT NULL;
  CREATE INDEX IF NOT EXISTS books_author_idx ON books (author);
`;

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  created_at: string;
  updated_at: string;
}

function toBook(row: BookRow): Book {
  return {
    id: row.id,
    title: row.title,
    author: row.author,
    year: row.year,
    isbn: row.isbn,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

/** Thrown when an insert/update would violate the unique ISBN constraint. */
export class DuplicateIsbnError extends Error {
  constructor(public readonly isbn: string) {
    super(`A book with ISBN ${isbn} already exists`);
    this.name = "DuplicateIsbnError";
  }
}

function isUniqueViolation(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "errcode" in err &&
    // SQLITE_CONSTRAINT_UNIQUE = 2067
    (err as { errcode?: number }).errcode === 2067
  );
}

/** Opens (and migrates) a SQLite database. Use ":memory:" for an ephemeral DB. */
export function openDatabase(path: string = ":memory:"): DatabaseSync {
  const db = new DatabaseSync(path);
  db.exec("PRAGMA journal_mode = WAL;");
  db.exec("PRAGMA foreign_keys = ON;");
  db.exec(SCHEMA);
  return db;
}

export class BookRepository {
  private readonly selectAll;
  private readonly selectByAuthor;
  private readonly selectById;
  private readonly insert;
  private readonly updateById;
  private readonly deleteById;

  constructor(private readonly db: DatabaseSync) {
    this.selectAll = db.prepare("SELECT * FROM books ORDER BY id");
    this.selectByAuthor = db.prepare(
      "SELECT * FROM books WHERE author = ? COLLATE NOCASE ORDER BY id",
    );
    this.selectById = db.prepare("SELECT * FROM books WHERE id = ?");
    this.insert = db.prepare(
      "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING *",
    );
    this.updateById = db.prepare(
      `UPDATE books
         SET title = ?, author = ?, year = ?, isbn = ?,
             updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
       WHERE id = ?
       RETURNING *`,
    );
    this.deleteById = db.prepare("DELETE FROM books WHERE id = ?");
  }

  list(author?: string): Book[] {
    const rows = (
      author === undefined
        ? this.selectAll.all()
        : this.selectByAuthor.all(author)
    ) as unknown as BookRow[];
    return rows.map(toBook);
  }

  get(id: number): Book | undefined {
    const row = this.selectById.get(id) as unknown as BookRow | undefined;
    return row ? toBook(row) : undefined;
  }

  create(input: BookInput): Book {
    try {
      const row = this.insert.get(
        input.title,
        input.author,
        input.year,
        input.isbn,
      ) as unknown as BookRow;
      return toBook(row);
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn) throw new DuplicateIsbnError(input.isbn);
      throw err;
    }
  }

  update(id: number, input: BookInput): Book | undefined {
    try {
      const row = this.updateById.get(
        input.title,
        input.author,
        input.year,
        input.isbn,
        id,
      ) as unknown as BookRow | undefined;
      return row ? toBook(row) : undefined;
    } catch (err) {
      if (isUniqueViolation(err) && input.isbn) throw new DuplicateIsbnError(input.isbn);
      throw err;
    }
  }

  delete(id: number): boolean {
    const result = this.deleteById.run(id);
    return Number(result.changes) > 0;
  }

  /** Test helper: remove every row. */
  clear(): void {
    this.db.exec("DELETE FROM books");
  }
}
