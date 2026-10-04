import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, it } from "node:test";
import { createApp } from "../src/app.ts";
import { BookStore } from "../src/store.ts";

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
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
  store.close();
});

async function call(method: string, path: string, body?: unknown) {
  const res = await fetch(base + path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
  const text = await res.text();
  return { status: res.status, headers: res.headers, body: text === "" ? undefined : JSON.parse(text) };
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" };

describe("GET /health", () => {
  it("reports ok", async () => {
    const res = await call("GET", "/health");
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, { status: "ok" });
    assert.match(res.headers.get("content-type") ?? "", /application\/json/);
  });
});

describe("POST /books", () => {
  it("creates a book and returns it with an id", async () => {
    const res = await call("POST", "/books", dune);
    assert.equal(res.status, 201);
    assert.deepEqual(res.body, { id: 1, ...dune });
    assert.equal(res.headers.get("location"), "/books/1");
  });

  it("accepts a book without year and isbn", async () => {
    const res = await call("POST", "/books", { title: "Emma", author: "Jane Austen" });
    assert.equal(res.status, 201);
    assert.deepEqual(res.body, { id: 1, title: "Emma", author: "Jane Austen", year: null, isbn: null });
  });

  it("rejects missing title and author", async () => {
    const res = await call("POST", "/books", { year: 1965 });
    assert.equal(res.status, 400);
    assert.equal(res.body.error, "validation failed");
    assert.equal(res.body.details.length, 2);
    assert.deepEqual((await call("GET", "/books")).body, []);
  });

  it("rejects blank title, non-integer year and non-string isbn", async () => {
    assert.equal((await call("POST", "/books", { ...dune, title: "   " })).status, 400);
    assert.equal((await call("POST", "/books", { ...dune, year: "1965" })).status, 400);
    assert.equal((await call("POST", "/books", { ...dune, year: 19.5 })).status, 400);
    assert.equal((await call("POST", "/books", { ...dune, isbn: 123 })).status, 400);
  });

  it("rejects malformed JSON and non-object bodies", async () => {
    assert.equal((await call("POST", "/books", "{not json")).status, 400);
    assert.equal((await call("POST", "/books", [dune])).status, 400);
  });

  it("rejects oversized bodies", async () => {
    const res = await call("POST", "/books", { ...dune, title: "x".repeat(1024 * 1024 + 1) });
    assert.equal(res.status, 413);
  });
});

describe("GET /books", () => {
  it("lists all books and filters by author", async () => {
    await call("POST", "/books", dune);
    await call("POST", "/books", { title: "Emma", author: "Jane Austen" });
    await call("POST", "/books", { title: "Children of Dune", author: "Frank Herbert" });

    const all = await call("GET", "/books");
    assert.equal(all.status, 200);
    assert.equal(all.body.length, 3);

    const filtered = await call("GET", "/books?author=" + encodeURIComponent("frank herbert"));
    assert.deepEqual(
      filtered.body.map((b: { title: string }) => b.title),
      ["Dune", "Children of Dune"],
    );

    assert.deepEqual((await call("GET", "/books?author=Nobody")).body, []);
  });
});

describe("GET /books/{id}", () => {
  it("returns the book", async () => {
    await call("POST", "/books", dune);
    const res = await call("GET", "/books/1");
    assert.equal(res.status, 200);
    assert.deepEqual(res.body, { id: 1, ...dune });
  });

  it("returns 404 for an unknown id and 400 for an invalid one", async () => {
    assert.equal((await call("GET", "/books/999")).status, 404);
    assert.equal((await call("GET", "/books/abc")).status, 400);
  });
});

describe("PUT /books/{id}", () => {
  it("replaces the book", async () => {
    await call("POST", "/books", dune);
    const res = await call("PUT", "/books/1", { title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
    assert.equal(res.status, 200);
    const expected = { id: 1, title: "Dune Messiah", author: "Frank Herbert", year: 1969, isbn: null };
    assert.deepEqual(res.body, expected);
    assert.deepEqual((await call("GET", "/books/1")).body, expected);
  });

  it("validates input and returns 404 for an unknown id", async () => {
    await call("POST", "/books", dune);
    assert.equal((await call("PUT", "/books/1", { title: "No author" })).status, 400);
    assert.equal((await call("PUT", "/books/999", dune)).status, 404);
    assert.deepEqual((await call("GET", "/books/1")).body, { id: 1, ...dune });
  });
});

describe("DELETE /books/{id}", () => {
  it("deletes the book", async () => {
    await call("POST", "/books", dune);
    const res = await call("DELETE", "/books/1");
    assert.equal(res.status, 204);
    assert.equal(res.body, undefined);
    assert.equal((await call("GET", "/books/1")).status, 404);
    assert.equal((await call("DELETE", "/books/1")).status, 404);
  });
});

describe("routing", () => {
  it("returns 404 for unknown paths and 405 for unsupported methods", async () => {
    assert.equal((await call("GET", "/nope")).status, 404);
    const res = await call("PATCH", "/books/1", {});
    assert.equal(res.status, 405);
    assert.equal(res.headers.get("allow"), "GET, PUT, DELETE");
  });
});

describe("persistence", () => {
  it("keeps ids unique after deletion", async () => {
    await call("POST", "/books", dune);
    await call("DELETE", "/books/1");
    assert.equal((await call("POST", "/books", dune)).body.id, 2);
  });
});
