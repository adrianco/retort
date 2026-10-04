import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, it } from "node:test";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/db.js";

let server: Server;
let store: BookStore;
let base: string;

async function start(): Promise<void> {
  store = new BookStore(":memory:");
  server = createApp(store).listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}

async function stop(): Promise<void> {
  await new Promise((resolve) => server.close(resolve));
  store.close();
}

function send(method: string, path: string, body?: unknown): Promise<Response> {
  return fetch(base + path, {
    method,
    headers: body === undefined ? {} : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" };

describe("books API", () => {
  // Fresh in-memory database per test.
  beforeEach(start);
  afterEach(stop);

  it("GET /health returns ok", async () => {
    const res = await send("GET", "/health");
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: "ok" });
  });

  it("POST /books creates a book", async () => {
    const res = await send("POST", "/books", dune);
    assert.equal(res.status, 201);
    assert.equal(res.headers.get("location"), "/books/1");
    assert.deepEqual(await res.json(), { id: 1, ...dune });
  });

  it("POST /books defaults optional fields to null", async () => {
    const res = await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
    assert.equal(res.status, 201);
    assert.deepEqual(await res.json(), { id: 1, title: "Emma", author: "Jane Austen", year: null, isbn: null });
  });

  it("POST /books rejects missing title and author", async () => {
    for (const body of [{ author: "A" }, { title: "T" }, { title: "  ", author: "A" }, {}, []]) {
      const res = await send("POST", "/books", body);
      assert.equal(res.status, 400, JSON.stringify(body));
      const json = (await res.json()) as { error: string; details: string[] };
      assert.equal(json.error, "validation failed");
      assert.ok(json.details.length > 0);
    }
    assert.deepEqual(await (await send("GET", "/books")).json(), []);
  });

  it("POST /books rejects bad year, bad isbn and malformed JSON", async () => {
    assert.equal((await send("POST", "/books", { ...dune, year: "1965" })).status, 400);
    assert.equal((await send("POST", "/books", { ...dune, year: 19.5 })).status, 400);
    assert.equal((await send("POST", "/books", { ...dune, isbn: 123 })).status, 400);
    const res = await fetch(base + "/books", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{not json",
    });
    assert.equal(res.status, 400);
    assert.deepEqual(await res.json(), { error: "invalid JSON body" });
  });

  it("GET /books lists all books and filters by author", async () => {
    await send("POST", "/books", dune);
    await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
    await send("POST", "/books", { title: "Children of Dune", author: "Frank Herbert" });

    const all = (await (await send("GET", "/books")).json()) as { title: string }[];
    assert.deepEqual(all.map((b) => b.title), ["Dune", "Emma", "Children of Dune"]);

    const res = await send("GET", "/books?author=" + encodeURIComponent("frank herbert"));
    assert.equal(res.status, 200);
    const filtered = (await res.json()) as { title: string }[];
    assert.deepEqual(filtered.map((b) => b.title), ["Dune", "Children of Dune"]);

    assert.deepEqual(await (await send("GET", "/books?author=Nobody")).json(), []);
  });

  it("GET /books/:id returns a book or 404", async () => {
    await send("POST", "/books", dune);
    const res = await send("GET", "/books/1");
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: 1, ...dune });

    for (const id of ["2", "abc", "0", "1.5"]) {
      const missing = await send("GET", `/books/${id}`);
      assert.equal(missing.status, 404, id);
      assert.deepEqual(await missing.json(), { error: "book not found" });
    }
  });

  it("PUT /books/:id updates a book", async () => {
    await send("POST", "/books", dune);
    const updated = { title: "Dune Messiah", author: "Frank Herbert", year: 1969, isbn: null };
    const res = await send("PUT", "/books/1", updated);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: 1, ...updated });
    assert.deepEqual(await (await send("GET", "/books/1")).json(), { id: 1, ...updated });
  });

  it("PUT /books/:id validates input and returns 404 for unknown ids", async () => {
    await send("POST", "/books", dune);
    assert.equal((await send("PUT", "/books/1", { title: "No author" })).status, 400);
    assert.deepEqual(await (await send("GET", "/books/1")).json(), { id: 1, ...dune });
    assert.equal((await send("PUT", "/books/99", dune)).status, 404);
  });

  it("DELETE /books/:id removes a book", async () => {
    await send("POST", "/books", dune);
    const res = await send("DELETE", "/books/1");
    assert.equal(res.status, 204);
    assert.equal(await res.text(), "");
    assert.equal((await send("GET", "/books/1")).status, 404);
    assert.equal((await send("DELETE", "/books/1")).status, 404);
  });

  it("unknown routes return JSON 404", async () => {
    const res = await send("GET", "/nope");
    assert.equal(res.status, 404);
    assert.deepEqual(await res.json(), { error: "not found" });
  });
});

describe("persistence", () => {
  it("keeps books across store instances on a file database", async () => {
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");
    const dir = mkdtempSync(join(tmpdir(), "books-"));
    try {
      const first = new BookStore(join(dir, "books.db"));
      first.create({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: null });
      first.close();
      const second = new BookStore(join(dir, "books.db"));
      assert.equal(second.list().length, 1);
      second.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
