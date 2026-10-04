import assert from "node:assert/strict";
import { Server } from "node:http";
import { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { createApp } from "../src/app";
import { BookStore } from "../src/db";

let server: Server;
let store: BookStore;
let base: string;

before(async () => {
  store = new BookStore(":memory:");
  server = createApp(store).listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

after(() => {
  server.close();
  store.close();
});

function send(method: string, path: string, body?: unknown) {
  return fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" };

test("GET /health returns ok", async () => {
  const res = await fetch(base + "/health");
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
});

test("POST /books creates a book and GET /books/:id returns it", async () => {
  const res = await send("POST", "/books", dune);
  assert.equal(res.status, 201);
  const created = await res.json();
  assert.deepEqual(created, { id: created.id, ...dune });

  const fetched = await fetch(`${base}/books/${created.id}`);
  assert.equal(fetched.status, 200);
  assert.deepEqual(await fetched.json(), created);
});

test("POST /books rejects missing title and author", async () => {
  const res = await send("POST", "/books", { year: 2000 });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.details.length, 2);

  assert.equal((await send("POST", "/books", { title: " ", author: "A" })).status, 400);
  assert.equal((await send("POST", "/books", { title: "T", author: "A", year: "x" })).status, 400);
});

test("POST /books rejects malformed JSON", async () => {
  const res = await fetch(base + "/books", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{nope",
  });
  assert.equal(res.status, 400);
});

test("GET /books lists books and filters by author", async () => {
  await send("POST", "/books", { title: "Emma", author: "Jane Austen" });
  await send("POST", "/books", { title: "Persuasion", author: "Jane Austen" });

  const all = await (await fetch(base + "/books")).json();
  assert.ok(all.length >= 3);

  const filtered = await (await fetch(base + "/books?author=Jane%20Austen")).json();
  assert.equal(filtered.length, 2);
  assert.ok(filtered.every((b: { author: string }) => b.author === "Jane Austen"));

  assert.deepEqual(await (await fetch(base + "/books?author=Nobody")).json(), []);
});

test("PUT /books/:id updates a book", async () => {
  const created = await (await send("POST", "/books", dune)).json();
  const res = await send("PUT", `/books/${created.id}`, { title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), {
    id: created.id,
    title: "Dune Messiah",
    author: "Frank Herbert",
    year: 1969,
    isbn: null,
  });

  assert.equal((await send("PUT", `/books/${created.id}`, { title: "No author" })).status, 400);
  assert.equal((await send("PUT", "/books/999999", dune)).status, 404);
});

test("DELETE /books/:id removes a book", async () => {
  const created = await (await send("POST", "/books", dune)).json();
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 204);
  assert.equal((await fetch(`${base}/books/${created.id}`)).status, 404);
  assert.equal((await send("DELETE", `/books/${created.id}`)).status, 404);
});

test("GET /books/:id returns 404 for unknown or invalid ids", async () => {
  assert.equal((await fetch(base + "/books/999999")).status, 404);
  assert.equal((await fetch(base + "/books/abc")).status, 404);
});
