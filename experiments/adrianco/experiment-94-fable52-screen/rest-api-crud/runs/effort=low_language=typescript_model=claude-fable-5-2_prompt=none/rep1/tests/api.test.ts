import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "../src/app.js";
import { BookStore } from "../src/db.js";

let server: Server;
let base: string;
const store = new BookStore(":memory:");

before(async () => {
  server = createApp(store).listen(0);
  await new Promise((r) => server.once("listening", r));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

after(() => {
  server.close();
  store.close();
});

const send = (method: string, path: string, body?: unknown) =>
  fetch(base + path, {
    method,
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

test("GET /health", async () => {
  const res = await fetch(base + "/health");
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("create and fetch a book", async () => {
  const res = await send("POST", "/books", { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" });
  assert.equal(res.status, 201);
  const book = await res.json();
  assert.equal(book.title, "Dune");
  assert.ok(Number.isInteger(book.id));

  const got = await fetch(`${base}/books/${book.id}`);
  assert.equal(got.status, 200);
  assert.deepEqual(await got.json(), book);
});

test("validation: title and author required", async () => {
  const res = await send("POST", "/books", { year: 2000 });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.deepEqual(body.details, ["title is required", "author is required"]);

  assert.equal((await send("POST", "/books", { title: " ", author: "A" })).status, 400);
  assert.equal((await send("POST", "/books", { title: "T", author: "A", year: "x" })).status, 400);
});

test("invalid JSON returns 400", async () => {
  const res = await fetch(base + "/books", { method: "POST", headers: { "content-type": "application/json" }, body: "{oops" });
  assert.equal(res.status, 400);
});

test("list with author filter", async () => {
  await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
  await send("POST", "/books", { title: "Persuasion", author: "Jane Austen" });
  const all = await (await fetch(base + "/books")).json();
  assert.ok(all.length >= 3);
  const filtered = await (await fetch(base + "/books?author=" + encodeURIComponent("Jane Austen"))).json();
  assert.deepEqual(filtered.map((b: { title: string }) => b.title), ["Emma", "Persuasion"]);
});

test("update a book", async () => {
  const created = await (await send("POST", "/books", { title: "Old", author: "Someone" })).json();
  const res = await send("PUT", `/books/${created.id}`, { title: "New", author: "Someone", year: 2020 });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { id: created.id, title: "New", author: "Someone", year: 2020, isbn: null });

  assert.equal((await send("PUT", `/books/${created.id}`, { title: "New" })).status, 400);
  assert.equal((await send("PUT", "/books/99999", { title: "X", author: "Y" })).status, 404);
});

test("delete a book", async () => {
  const created = await (await send("POST", "/books", { title: "Temp", author: "Nobody" })).json();
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 204);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 404);
  assert.equal((await fetch(base + "/books/abc")).status, 404);
});
