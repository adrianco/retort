import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, it } from "node:test";
import { createApp } from "../src/app";
import { BookStore } from "../src/db";

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
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" };

describe("GET /health", () => {
  it("returns ok", async () => {
    const res = await fetch(base + "/health");
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the new resource", async () => {
    const res = await send("POST", "/books", dune);
    assert.equal(res.status, 201);
    assert.equal(res.headers.get("location"), "/books/1");
    assert.deepEqual(await res.json(), { id: 1, ...dune });
  });

  it("accepts a book without year and isbn", async () => {
    const res = await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
    assert.equal(res.status, 201);
    assert.deepEqual(await res.json(), { id: 1, title: "Emma", author: "Jane Austen", year: null, isbn: null });
  });

  it("rejects missing title and author with 400", async () => {
    const res = await send("POST", "/books", { year: 1965 });
    assert.equal(res.status, 400);
    const body = (await res.json()) as { details: string[] };
    assert.equal(body.details.length, 2);
    assert.match(body.details[0], /title/);
    assert.match(body.details[1], /author/);
  });

  it("rejects blank title, non-integer year and non-string isbn", async () => {
    for (const bad of [
      { ...dune, title: "   " },
      { ...dune, author: 42 },
      { ...dune, year: "1965" },
      { ...dune, year: 19.5 },
      { ...dune, isbn: 123 },
    ]) {
      const res = await send("POST", "/books", bad);
      assert.equal(res.status, 400, JSON.stringify(bad));
    }
    assert.deepEqual(store.list(), []);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await fetch(base + "/books", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{not json",
    });
    assert.equal(res.status, 400);
    assert.ok(((await res.json()) as { error: string }).error);
  });
});

describe("GET /books", () => {
  it("lists all books and filters by author", async () => {
    await send("POST", "/books", dune);
    await send("POST", "/books", { title: "Emma", author: "Jane Austen", year: 1815 });
    await send("POST", "/books", { title: "Children of Dune", author: "Frank Herbert", year: 1976 });

    const all = (await (await fetch(base + "/books")).json()) as { title: string }[];
    assert.deepEqual(all.map((b) => b.title), ["Dune", "Emma", "Children of Dune"]);

    const res = await fetch(base + "/books?author=" + encodeURIComponent("Frank Herbert"));
    assert.equal(res.status, 200);
    const filtered = (await res.json()) as { title: string }[];
    assert.deepEqual(filtered.map((b) => b.title), ["Dune", "Children of Dune"]);

    const none = await (await fetch(base + "/books?author=Nobody")).json();
    assert.deepEqual(none, []);
  });
});

describe("GET /books/:id", () => {
  it("returns the book", async () => {
    await send("POST", "/books", dune);
    const res = await fetch(base + "/books/1");
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: 1, ...dune });
  });

  it("returns 404 for an unknown id and 400 for an invalid id", async () => {
    assert.equal((await fetch(base + "/books/999")).status, 404);
    assert.equal((await fetch(base + "/books/abc")).status, 400);
  });
});

describe("PUT /books/:id", () => {
  it("replaces the book", async () => {
    await send("POST", "/books", dune);
    const updated = { title: "Dune Messiah", author: "Frank Herbert", year: 1969, isbn: null };
    const res = await send("PUT", "/books/1", updated);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: 1, ...updated });
    assert.deepEqual(await (await fetch(base + "/books/1")).json(), { id: 1, ...updated });
  });

  it("returns 400 for invalid input and 404 for an unknown id", async () => {
    await send("POST", "/books", dune);
    assert.equal((await send("PUT", "/books/1", { title: "No author" })).status, 400);
    assert.equal((await send("PUT", "/books/999", dune)).status, 404);
    assert.deepEqual(await (await fetch(base + "/books/1")).json(), { id: 1, ...dune });
  });
});

describe("DELETE /books/:id", () => {
  it("deletes the book and returns 204, then 404", async () => {
    await send("POST", "/books", dune);
    const res = await send("DELETE", "/books/1");
    assert.equal(res.status, 204);
    assert.equal((await fetch(base + "/books/1")).status, 404);
    assert.equal((await send("DELETE", "/books/1")).status, 404);
  });
});
