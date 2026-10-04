import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, it } from "node:test";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/store.js";

let store: BookStore;
let server: Server;
let base: string;

beforeEach(async () => {
  store = new BookStore(":memory:");
  server = createApp(store);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterEach(async () => {
  await new Promise((resolve) => server.close(resolve));
  store.close();
});

function send(method: string, path: string, body?: unknown): Promise<Response> {
  return fetch(base + path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" };
const emma = { title: "Emma", author: "Jane Austen", year: 1815, isbn: "9780141439587" };

describe("GET /health", () => {
  it("returns ok", async () => {
    const res = await send("GET", "/health");
    assert.equal(res.status, 200);
    assert.match(res.headers.get("content-type") ?? "", /application\/json/);
    assert.deepEqual(await res.json(), { status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the new resource", async () => {
    const res = await send("POST", "/books", dune);
    assert.equal(res.status, 201);
    const book = await res.json();
    assert.deepEqual(book, { id: book.id, ...dune });
    assert.equal(res.headers.get("location"), `/books/${book.id}`);
  });

  it("accepts a book without year and isbn", async () => {
    const res = await send("POST", "/books", { title: "Untitled", author: "Anon" });
    assert.equal(res.status, 201);
    assert.deepEqual(await res.json(), { id: 1, title: "Untitled", author: "Anon", year: null, isbn: null });
  });

  it("rejects a missing title and author with 400", async () => {
    const res = await send("POST", "/books", { year: 2000 });
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.equal(body.error, "validation failed");
    assert.equal(body.details.length, 2);
  });

  it("rejects blank title, non-integer year and malformed JSON", async () => {
    assert.equal((await send("POST", "/books", { ...dune, title: "   " })).status, 400);
    assert.equal((await send("POST", "/books", { ...dune, year: "1965" })).status, 400);
    assert.equal((await send("POST", "/books", { ...dune, year: 19.5 })).status, 400);
    assert.equal((await send("POST", "/books", "{not json")).status, 400);
    assert.equal((await send("POST", "/books", [dune])).status, 400);
    assert.deepEqual(await (await send("GET", "/books")).json(), []);
  });
});

describe("GET /books", () => {
  it("lists all books", async () => {
    await send("POST", "/books", dune);
    await send("POST", "/books", emma);
    const res = await send("GET", "/books");
    assert.equal(res.status, 200);
    const books = await res.json();
    assert.deepEqual(books.map((b: { title: string }) => b.title), ["Dune", "Emma"]);
  });

  it("filters by author", async () => {
    await send("POST", "/books", dune);
    await send("POST", "/books", emma);
    await send("POST", "/books", { title: "Persuasion", author: "Jane Austen" });
    const res = await send("GET", `/books?author=${encodeURIComponent("Jane Austen")}`);
    const books = await res.json();
    assert.deepEqual(books.map((b: { title: string }) => b.title), ["Emma", "Persuasion"]);
    assert.deepEqual(await (await send("GET", "/books?author=Nobody")).json(), []);
  });
});

describe("GET /books/{id}", () => {
  it("returns a single book", async () => {
    const created = await (await send("POST", "/books", dune)).json();
    const res = await send("GET", `/books/${created.id}`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), created);
  });

  it("returns 404 for an unknown id and 400 for an invalid id", async () => {
    assert.equal((await send("GET", "/books/999")).status, 404);
    assert.equal((await send("GET", "/books/abc")).status, 400);
  });
});

describe("PUT /books/{id}", () => {
  it("updates a book", async () => {
    const created = await (await send("POST", "/books", dune)).json();
    const res = await send("PUT", `/books/${created.id}`, { ...dune, title: "Dune Messiah", year: 1969 });
    assert.equal(res.status, 200);
    const expected = { ...created, title: "Dune Messiah", year: 1969 };
    assert.deepEqual(await res.json(), expected);
    assert.deepEqual(await (await send("GET", `/books/${created.id}`)).json(), expected);
  });

  it("validates input and returns 404 for an unknown id", async () => {
    const created = await (await send("POST", "/books", dune)).json();
    assert.equal((await send("PUT", `/books/${created.id}`, { title: "No author" })).status, 400);
    assert.equal((await send("PUT", "/books/999", dune)).status, 404);
  });
});

describe("DELETE /books/{id}", () => {
  it("deletes a book", async () => {
    const created = await (await send("POST", "/books", dune)).json();
    assert.equal((await send("DELETE", `/books/${created.id}`)).status, 204);
    assert.equal((await send("GET", `/books/${created.id}`)).status, 404);
    assert.equal((await send("DELETE", `/books/${created.id}`)).status, 404);
  });
});

describe("routing", () => {
  it("returns 404 for unknown paths and 405 for unsupported methods", async () => {
    assert.equal((await send("GET", "/nope")).status, 404);
    const res = await send("PATCH", "/books");
    assert.equal(res.status, 405);
    assert.equal(res.headers.get("allow"), "GET, POST");
  });
});

describe("BookStore persistence", () => {
  it("persists books to a SQLite file across instances", async () => {
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");
    const dir = mkdtempSync(join(tmpdir(), "books-"));
    try {
      const first = new BookStore(join(dir, "books.db"));
      const created = first.create(dune);
      first.close();
      const second = new BookStore(join(dir, "books.db"));
      assert.deepEqual({ ...second.get(created.id) }, created);
      second.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
