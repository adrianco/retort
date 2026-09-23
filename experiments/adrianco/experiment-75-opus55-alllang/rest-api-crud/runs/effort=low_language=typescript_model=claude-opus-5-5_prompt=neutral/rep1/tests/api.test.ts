import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { createApp } from "../src/app.js";

let server: Server;
let base: string;

before(async () => {
  server = createApp(":memory:");
  await new Promise<void>((r) => server.listen(0, r));
  base = `http://localhost:${(server.address() as AddressInfo).port}`;
});
after(() => new Promise<void>((r) => server.close(() => r())));

const req = (path: string, method = "GET", body?: unknown) =>
  fetch(base + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });

test("health check", async () => {
  const r = await req("/health");
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { status: "ok" });
});

test("full CRUD lifecycle", async () => {
  let r = await req("/books", "POST", { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441013593" });
  assert.equal(r.status, 201);
  const book = await r.json();
  assert.equal(book.title, "Dune");
  assert.ok(book.id);

  r = await req(`/books/${book.id}`);
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), book);

  r = await req(`/books/${book.id}`, "PUT", { title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).title, "Dune Messiah");

  r = await req(`/books/${book.id}`, "DELETE");
  assert.equal(r.status, 204);
  r = await req(`/books/${book.id}`);
  assert.equal(r.status, 404);
  r = await req(`/books/${book.id}`, "DELETE");
  assert.equal(r.status, 404);
});

test("list with author filter", async () => {
  await req("/books", "POST", { title: "Emma", author: "Jane Austen" });
  await req("/books", "POST", { title: "Persuasion", author: "Jane Austen" });
  await req("/books", "POST", { title: "Ulysses", author: "James Joyce" });
  let r = await req("/books?author=Jane%20Austen");
  assert.equal(r.status, 200);
  const list = await r.json();
  assert.equal(list.length, 2);
  assert.ok(list.every((b: { author: string }) => b.author === "Jane Austen"));
  r = await req("/books");
  assert.ok((await r.json()).length >= 3);
});

test("validation errors", async () => {
  let r = await req("/books", "POST", { author: "Nobody" });
  assert.equal(r.status, 400);
  assert.deepEqual((await r.json()).details, ["title is required"]);
  r = await req("/books", "POST", { title: "X", author: "  " });
  assert.equal(r.status, 400);
  r = await req("/books", "POST", { title: "X", author: "Y", year: "abc" });
  assert.equal(r.status, 400);
  r = await req("/books", "POST", "{not json");
  assert.equal(r.status, 400);
  r = await req("/books/1", "PUT", {});
  assert.equal(r.status, 400);
  r = await req("/books/abc");
  assert.equal(r.status, 400);
  r = await req("/books/9999", "PUT", { title: "a", author: "b" });
  assert.equal(r.status, 404);
});
