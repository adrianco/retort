import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "../src/app.ts";
import { BookStore } from "../src/db.ts";

let server: Server;
let store: BookStore;
let base: string;

before(async () => {
  store = new BookStore(":memory:");
  server = createApp(store);
  await new Promise<void>((resolve) => server.listen(0, resolve));
  base = `http://localhost:${(server.address() as AddressInfo).port}`;
});

after(() => {
  server.close();
  store.close();
});

function call(method: string, path: string, body?: unknown): Promise<Response> {
  return fetch(base + path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" };

test("GET /health returns ok", async () => {
  const res = await call("GET", "/health");
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("POST /books creates a book and GET /books/:id returns it", async () => {
  const res = await call("POST", "/books", dune);
  assert.equal(res.status, 201);
  const created = (await res.json()) as { id: number };
  assert.deepEqual(created, { id: created.id, ...dune });
  assert.equal(res.headers.get("location"), `/books/${created.id}`);

  const fetched = await call("GET", `/books/${created.id}`);
  assert.equal(fetched.status, 200);
  assert.deepEqual(await fetched.json(), created);
});

test("POST /books validates required fields", async () => {
  const res = await call("POST", "/books", { title: "  ", year: "old" });
  assert.equal(res.status, 400);
  const body = (await res.json()) as { details: string[] };
  assert.equal(body.details.length, 3);

  const bad = await fetch(base + "/books", { method: "POST", body: "{nope" });
  assert.equal(bad.status, 400);
});

test("POST /books allows optional year and isbn", async () => {
  const res = await call("POST", "/books", { title: "Untitled", author: "Anon" });
  assert.equal(res.status, 201);
  const body = (await res.json()) as { year: null; isbn: null };
  assert.equal(body.year, null);
  assert.equal(body.isbn, null);
});

test("GET /books lists books and filters by author", async () => {
  await call("POST", "/books", { title: "Emma", author: "Jane Austen", year: 1815 });
  const all = (await (await call("GET", "/books")).json()) as unknown[];
  assert.ok(all.length >= 2);

  const res = await call("GET", "/books?author=Jane%20Austen");
  assert.equal(res.status, 200);
  const filtered = (await res.json()) as { author: string }[];
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0]?.author, "Jane Austen");

  assert.deepEqual(await (await call("GET", "/books?author=Nobody")).json(), []);
});

test("PUT /books/:id updates a book", async () => {
  const { id } = (await (await call("POST", "/books", dune)).json()) as { id: number };
  const res = await call("PUT", `/books/${id}`, { ...dune, title: "Dune Messiah", year: 1969 });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { id, ...dune, title: "Dune Messiah", year: 1969 });

  assert.equal((await call("PUT", `/books/${id}`, { author: "x" })).status, 400);
  assert.equal((await call("PUT", "/books/999999", dune)).status, 404);
});

test("DELETE /books/:id removes a book", async () => {
  const { id } = (await (await call("POST", "/books", dune)).json()) as { id: number };
  assert.equal((await call("DELETE", `/books/${id}`)).status, 204);
  assert.equal((await call("GET", `/books/${id}`)).status, 404);
  assert.equal((await call("DELETE", `/books/${id}`)).status, 404);
});

test("unknown routes, ids and methods are rejected", async () => {
  assert.equal((await call("GET", "/nope")).status, 404);
  assert.equal((await call("GET", "/books/abc")).status, 404);
  assert.equal((await call("PATCH", "/books")).status, 405);
});
