import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { DatabaseSync } from "node:sqlite";
import { openDatabase } from "../src/db.js";
import { BookRepository, DuplicateIsbnError } from "../src/repository.js";

let db: DatabaseSync;
let repo: BookRepository;

beforeEach(() => {
  db = openDatabase(":memory:");
  repo = new BookRepository(db);
});

afterEach(() => {
  db.close();
});

describe("BookRepository", () => {
  it("round-trips a book through create/findById", () => {
    const book = repo.create({ title: "Snow Crash", author: "Neal Stephenson", year: 1992, isbn: "9780553380958" });
    expect(book.id).toBe(1);
    expect(repo.findById(1)).toEqual(book);
  });

  it("stores null for omitted optional fields", () => {
    const book = repo.create({ title: "T", author: "A" });
    expect(book.year).toBeNull();
    expect(book.isbn).toBeNull();
  });

  it("throws DuplicateIsbnError on a duplicate isbn but allows multiple null isbns", () => {
    repo.create({ title: "A", author: "X", isbn: "9780553380958" });
    expect(() => repo.create({ title: "B", author: "Y", isbn: "9780553380958" })).toThrow(DuplicateIsbnError);
    expect(() => repo.create({ title: "C", author: "Z" })).not.toThrow();
    expect(() => repo.create({ title: "D", author: "W" })).not.toThrow();
  });

  it("update returns undefined for a missing id and delete returns false", () => {
    expect(repo.update(99, { title: "T", author: "A" })).toBeUndefined();
    expect(repo.delete(99)).toBe(false);
  });

  it("filters by author", () => {
    repo.create({ title: "A", author: "Ursula K. Le Guin" });
    repo.create({ title: "B", author: "Ursula K. Le Guin" });
    repo.create({ title: "C", author: "Octavia Butler" });
    expect(repo.findAll({ author: "ursula k. le guin" })).toHaveLength(2);
    expect(repo.findAll()).toHaveLength(3);
  });
});
