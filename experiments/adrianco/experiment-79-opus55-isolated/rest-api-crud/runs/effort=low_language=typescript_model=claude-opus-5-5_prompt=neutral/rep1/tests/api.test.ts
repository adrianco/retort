import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, it } from "node:test";
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
  await new Promise((resolve) => server.close(resolve));
  store.close();
});

function send(method: string, path: string, body?: unknown): Promise<Response> {
  return fetch(base + path, {
    method,
    headers: body === undefined ? {} : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" };

describe("books API", () => {
  it("GET /health returns ok", async () => {
    const res = await send("GET", "/health");
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: "ok" });
  });

  it("POST /books creates a book and GET /books/:id returns it", async () => {
    const res = await send("POST", "/books", dune);
    assert.equal(res.status, 201);
    const created = await res.json();
    assert.deepEqual(created, { id: 1, ...dune });
    assert.equal(res.headers.get("location"), "/books/1");

    const fetched = await send("GET", "/books/1");
    assert.equal(fetched.status, 200);
    assert.deepEqual(await fetched.json(), created);
  });

  it("POST /books allows year and isbn to be omitted", async () => {
    const res = await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
    assert.equal(res.status, 201);
    assert.deepEqual(await res.json(), { id: 1, title: "Emma", author: "Jane Austen", year: null, isbn: null });
  });

  it("POST /books rejects missing title and author", async () => {
    const res = await send("POST", "/books", { year: 1999 });
    assert.equal(res.status, 400);
    const body = (await res.json()) as { details: string[] };
    assert.equal(body.details.length, 2);

    assert.equal((await send("POST", "/books", { title: "  ", author: "A" })).status, 400);
    assert.equal((await send("POST", "/books", { title: "T", author: "A", year: "x" })).status, 400);
  });

  it("POST /books rejects malformed JSON with 400", async () => {
    const res = await fetch(base + "/books", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{not json",
    });
    assert.equal(res.status, 400);
    assert.ok(((await res.json()) as { error: string }).error);
  });

  it("GET /books lists all books and filters by author", async () => {
    await send("POST", "/books", dune);
    await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
    await send("POST", "/books", { title: "Children of Dune", author: "Frank Herbert" });

    const all = (await (await send("GET", "/books")).json()) as unknown[];
    assert.equal(all.length, 3);

    const filtered = (await (await send("GET", "/books?author=Frank%20Herbert")).json()) as { title: string }[];
    assert.deepEqual(filtered.map((b) => b.title), ["Dune", "Children of Dune"]);

    assert.deepEqual(await (await send("GET", "/books?author=Nobody")).json(), []);
  });

  it("PUT /books/:id updates a book", async () => {
    await send("POST", "/books", dune);
    const res = await send("PUT", "/books/1", { ...dune, title: "Dune Messiah", year: 1969 });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { id: 1, ...dune, title: "Dune Messiah", year: 1969 });
    assert.equal(((await (await send("GET", "/books/1")).json()) as { title: string }).title, "Dune Messiah");

    assert.equal((await send("PUT", "/books/1", { author: "x" })).status, 400);
    assert.equal((await send("PUT", "/books/99", dune)).status, 404);
  });

  it("DELETE /books/:id removes a book", async () => {
    await send("POST", "/books", dune);
    assert.equal((await send("DELETE", "/books/1")).status, 204);
    assert.equal((await send("GET", "/books/1")).status, 404);
    assert.equal((await send("DELETE", "/books/1")).status, 404);
  });

  it("returns 404 for unknown or non-numeric ids", async () => {
    assert.equal((await send("GET", "/books/42")).status, 404);
    assert.equal((await send("GET", "/books/abc")).status, 404);
  });
});
