import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "../src/app.js";

let server: Server;
let base: string;

before(async () => {
  server = createApp(":memory:").listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

after(() => {
  server.close();
});

const send = (method: string, path: string, body?: unknown) =>
  fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

test("GET /health returns ok", async () => {
  const res = await fetch(`${base}/health`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("POST /books creates a book and GET retrieves it", async () => {
  const res = await send("POST", "/books", { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441172719" });
  assert.equal(res.status, 201);
  const book = await res.json();
  assert.equal(book.title, "Dune");
  assert.equal(typeof book.id, "number");

  const got = await fetch(`${base}/books/${book.id}`);
  assert.equal(got.status, 200);
  assert.deepEqual(await got.json(), book);
});

test("POST /books validates required fields", async () => {
  const res = await send("POST", "/books", { year: 2000 });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.deepEqual(body.details, ["title is required", "author is required"]);

  const bad = await send("POST", "/books", { title: "T", author: "A", year: "soon" });
  assert.equal(bad.status, 400);
});

test("malformed JSON returns 400", async () => {
  const res = await fetch(`${base}/books`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{oops" });
  assert.equal(res.status, 400);
});

test("GET /books lists and filters by author", async () => {
  await send("POST", "/books", { title: "Emma", author: "Jane Austen", year: 1815 });
  await send("POST", "/books", { title: "Persuasion", author: "Jane Austen" });
  const all = await (await fetch(`${base}/books`)).json();
  assert.ok(all.length >= 3);

  const filtered = await (await fetch(`${base}/books?author=${encodeURIComponent("Jane Austen")}`)).json();
  assert.equal(filtered.length, 2);
  assert.ok(filtered.every((b: { author: string }) => b.author === "Jane Austen"));
});

test("PUT /books/:id updates a book", async () => {
  const created = await (await send("POST", "/books", { title: "Old", author: "Someone" })).json();
  const res = await send("PUT", `/books/${created.id}`, { title: "New", author: "Someone", year: 2020 });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { id: created.id, title: "New", author: "Someone", year: 2020, isbn: null });

  assert.equal((await send("PUT", `/books/${created.id}`, { title: "" })).status, 400);
  assert.equal((await send("PUT", "/books/99999", { title: "X", author: "Y" })).status, 404);
});

test("DELETE /books/:id removes a book", async () => {
  const created = await (await send("POST", "/books", { title: "Gone", author: "Nobody" })).json();
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 204);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 404);
});
