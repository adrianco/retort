import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, test } from "node:test";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/db.js";

let store: BookStore;
let server: Server;
let base: string;

beforeEach(async () => {
  store = new BookStore(":memory:");
  server = createApp(store).listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterEach(async () => {
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
  store.close();
});

function send(method: string, path: string, body?: unknown): Promise<globalThis.Response> {
  return fetch(base + path, {
    method,
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" };

test("GET /health returns ok", async () => {
  const res = await fetch(`${base}/health`);
  assert.equal(res.status, 200);
  assert.match(res.headers.get("content-type") ?? "", /application\/json/);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("POST /books creates a book and GET /books/:id returns it", async () => {
  const created = await send("POST", "/books", dune);
  assert.equal(created.status, 201);
  const book = await created.json();
  assert.deepEqual(book, { id: 1, ...dune });
  assert.equal(created.headers.get("location"), "/books/1");

  const fetched = await fetch(`${base}/books/1`);
  assert.equal(fetched.status, 200);
  assert.deepEqual(await fetched.json(), book);
});

test("POST /books allows year and isbn to be omitted", async () => {
  const res = await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
  assert.equal(res.status, 201);
  assert.deepEqual(await res.json(), { id: 1, title: "Emma", author: "Jane Austen", year: null, isbn: null });
});

test("POST /books rejects missing or invalid fields with 400", async () => {
  const cases: unknown[] = [
    {},
    { title: "No author" },
    { author: "No title" },
    { title: "   ", author: "Blank title" },
    { title: 42, author: "Wrong type" },
    { title: "T", author: "A", year: "1999" },
    { title: "T", author: "A", year: 19.5 },
    { title: "T", author: "A", isbn: 123 },
    ["not", "an", "object"],
  ];
  for (const body of cases) {
    const res = await send("POST", "/books", body);
    assert.equal(res.status, 400, JSON.stringify(body));
    const json = (await res.json()) as { error: string; details: string[] };
    assert.equal(json.error, "validation failed");
    assert.ok(json.details.length > 0);
  }
  const missingBoth = (await (await send("POST", "/books", {})).json()) as { details: string[] };
  assert.equal(missingBoth.details.length, 2);
  assert.deepEqual(await (await fetch(`${base}/books`)).json(), []);
});

test("POST /books with malformed JSON returns 400", async () => {
  const res = await send("POST", "/books", "{not json");
  assert.equal(res.status, 400);
  assert.deepEqual(await res.json(), { error: "invalid JSON body" });
});

test("GET /books lists all books and filters by author", async () => {
  await send("POST", "/books", dune);
  await send("POST", "/books", { title: "Emma", author: "Jane Austen", year: 1815 });
  await send("POST", "/books", { title: "Dune Messiah", author: "Frank Herbert", year: 1969 });

  const all = (await (await fetch(`${base}/books`)).json()) as { title: string }[];
  assert.deepEqual(all.map((b) => b.title), ["Dune", "Emma", "Dune Messiah"]);

  const res = await fetch(`${base}/books?author=${encodeURIComponent("Frank Herbert")}`);
  assert.equal(res.status, 200);
  const filtered = (await res.json()) as { title: string }[];
  assert.deepEqual(filtered.map((b) => b.title), ["Dune", "Dune Messiah"]);

  const none = await fetch(`${base}/books?author=Nobody`);
  assert.equal(none.status, 200);
  assert.deepEqual(await none.json(), []);
});

test("GET /books/:id returns 404 for unknown and 400 for invalid ids", async () => {
  assert.equal((await fetch(`${base}/books/999`)).status, 404);
  assert.equal((await fetch(`${base}/books/abc`)).status, 400);
  assert.equal((await fetch(`${base}/books/0`)).status, 400);
});

test("PUT /books/:id updates a book", async () => {
  await send("POST", "/books", dune);
  const res = await send("PUT", "/books/1", { title: "Dune (Revised)", author: "Frank Herbert", year: 1966 });
  assert.equal(res.status, 200);
  const expected = { id: 1, title: "Dune (Revised)", author: "Frank Herbert", year: 1966, isbn: null };
  assert.deepEqual(await res.json(), expected);
  assert.deepEqual(await (await fetch(`${base}/books/1`)).json(), expected);
});

test("PUT /books/:id validates input and returns 404 for unknown id", async () => {
  await send("POST", "/books", dune);
  assert.equal((await send("PUT", "/books/1", { title: "Only title" })).status, 400);
  assert.equal((await send("PUT", "/books/999", dune)).status, 404);
  assert.deepEqual(await (await fetch(`${base}/books/1`)).json(), { id: 1, ...dune });
});

test("DELETE /books/:id removes a book", async () => {
  await send("POST", "/books", dune);
  const res = await send("DELETE", "/books/1");
  assert.equal(res.status, 204);
  assert.equal((await fetch(`${base}/books/1`)).status, 404);
  assert.equal((await send("DELETE", "/books/1")).status, 404);
});

test("unknown routes return a JSON 404", async () => {
  const res = await fetch(`${base}/nope`);
  assert.equal(res.status, 404);
  assert.deepEqual(await res.json(), { error: "not found" });
});

test("data persists in a SQLite file across store instances", async (t) => {
  const { mkdtempSync, rmSync } = await import("node:fs");
  const { tmpdir } = await import("node:os");
  const { join } = await import("node:path");
  const dir = mkdtempSync(join(tmpdir(), "books-"));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const path = join(dir, "books.db");

  const first = new BookStore(path);
  const created = first.create({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: null });
  first.close();

  const second = new BookStore(path);
  assert.deepEqual({ ...second.get(created.id) }, created);
  second.close();
});
