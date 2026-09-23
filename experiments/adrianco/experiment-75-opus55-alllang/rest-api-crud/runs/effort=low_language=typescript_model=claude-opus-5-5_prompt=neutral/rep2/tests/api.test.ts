import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { createApp } from "../src/app.js";

const server = createApp();
let base = "";
before(async () => {
  await new Promise<void>((r) => server.listen(0, r));
  base = `http://localhost:${(server.address() as AddressInfo).port}`;
});
after(() => server.close());

const req = (path: string, method = "GET", body?: unknown) =>
  fetch(base + path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });

test("health check", async () => {
  const r = await req("/health");
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { status: "ok" });
});

test("validation: title and author required", async () => {
  const r = await req("/books", "POST", { year: 2000 });
  assert.equal(r.status, 400);
  const body = (await r.json()) as { errors: string[] };
  assert.ok(body.errors.includes("title is required"));
  assert.ok(body.errors.includes("author is required"));
  assert.equal((await req("/books", "POST", { title: "x", author: "y", year: "abc" })).status, 400);
});

test("invalid JSON returns 400", async () => {
  const r = await fetch(base + "/books", { method: "POST", body: "{bad" });
  assert.equal(r.status, 400);
});

test("full CRUD lifecycle and author filter", async () => {
  const c = await req("/books", "POST", { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" });
  assert.equal(c.status, 201);
  const book = (await c.json()) as { id: number; title: string };
  assert.equal(book.title, "Dune");
  await req("/books", "POST", { title: "Emma", author: "Jane Austen" });

  const all = (await (await req("/books")).json()) as unknown[];
  assert.ok(all.length >= 2);
  const filtered = (await (await req("/books?author=frank%20herbert")).json()) as { author: string }[];
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].author, "Frank Herbert");

  assert.equal((await req(`/books/${book.id}`)).status, 200);
  const u = await req(`/books/${book.id}`, "PUT", { title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
  assert.equal(u.status, 200);
  assert.equal(((await u.json()) as { title: string }).title, "Dune Messiah");
  assert.equal((await req(`/books/${book.id}`, "PUT", { title: "" })).status, 400);

  assert.equal((await req(`/books/${book.id}`, "DELETE")).status, 204);
  assert.equal((await req(`/books/${book.id}`)).status, 404);
  assert.equal((await req(`/books/${book.id}`, "DELETE")).status, 404);
  assert.equal((await req("/books/9999", "PUT", { title: "a", author: "b" })).status, 404);
});
