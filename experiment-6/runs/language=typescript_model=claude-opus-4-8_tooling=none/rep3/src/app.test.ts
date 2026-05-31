import { test, beforeEach, afterEach, describe } from "node:test";
import assert from "node:assert/strict";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { createApp } from "./app.ts";
import { createDb } from "./db.ts";

/**
 * Spin up the app on an ephemeral port backed by an in-memory DB,
 * returning a base URL and a teardown function.
 */
function startServer(): Promise<{ baseUrl: string; close: () => Promise<void> }> {
  const db = createDb(":memory:");
  const app = createApp(db);
  return new Promise((resolve) => {
    const server: Server = app.listen(0, () => {
      const { port } = server.address() as AddressInfo;
      resolve({
        baseUrl: `http://127.0.0.1:${port}`,
        close: () =>
          new Promise<void>((res) => {
            server.close(() => {
              db.close();
              res();
            });
          }),
      });
    });
  });
}

describe("Book Collection API", () => {
  let baseUrl: string;
  let close: () => Promise<void>;

  beforeEach(async () => {
    ({ baseUrl, close } = await startServer());
  });

  afterEach(async () => {
    if (close) await close();
  });

  test("GET /health returns ok", async () => {
    const res = await fetch(`${baseUrl}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: "ok" });
  });

  test("POST /books creates a book and returns 201", async () => {
    const res = await fetch(`${baseUrl}/books`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "The Pragmatic Programmer",
        author: "Andy Hunt",
        year: 1999,
        isbn: "978-0201616224",
      }),
    });
    assert.equal(res.status, 201);
    const book = await res.json();
    assert.equal(book.title, "The Pragmatic Programmer");
    assert.equal(book.author, "Andy Hunt");
    assert.equal(book.year, 1999);
    assert.ok(typeof book.id === "number");
  });

  test("POST /books rejects missing title/author with 400", async () => {
    const res = await fetch(`${baseUrl}/books`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ year: 2020 }),
    });
    assert.equal(res.status, 400);
    const body = await res.json();
    assert.ok(Array.isArray(body.errors));
    assert.equal(body.errors.length, 2);
  });

  test("GET /books lists all books and supports ?author= filter", async () => {
    const post = (b: object) =>
      fetch(`${baseUrl}/books`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(b),
      });
    await post({ title: "Book A", author: "Alice" });
    await post({ title: "Book B", author: "Bob" });
    await post({ title: "Book C", author: "Alice" });

    const all = await (await fetch(`${baseUrl}/books`)).json();
    assert.equal(all.length, 3);

    const byAlice = await (
      await fetch(`${baseUrl}/books?author=Alice`)
    ).json();
    assert.equal(byAlice.length, 2);
    assert.ok(byAlice.every((b: { author: string }) => b.author === "Alice"));
  });

  test("GET /books/:id returns a book or 404", async () => {
    const created = await (
      await fetch(`${baseUrl}/books`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Solo", author: "Han" }),
      })
    ).json();

    const found = await fetch(`${baseUrl}/books/${created.id}`);
    assert.equal(found.status, 200);
    assert.equal((await found.json()).title, "Solo");

    const missing = await fetch(`${baseUrl}/books/99999`);
    assert.equal(missing.status, 404);
  });

  test("PUT /books/:id updates a book", async () => {
    const created = await (
      await fetch(`${baseUrl}/books`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Old", author: "Author" }),
      })
    ).json();

    const res = await fetch(`${baseUrl}/books/${created.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New", author: "Author", year: 2024 }),
    });
    assert.equal(res.status, 200);
    const updated = await res.json();
    assert.equal(updated.title, "New");
    assert.equal(updated.year, 2024);
  });

  test("DELETE /books/:id removes a book and returns 204", async () => {
    const created = await (
      await fetch(`${baseUrl}/books`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Doomed", author: "Author" }),
      })
    ).json();

    const del = await fetch(`${baseUrl}/books/${created.id}`, {
      method: "DELETE",
    });
    assert.equal(del.status, 204);

    const after = await fetch(`${baseUrl}/books/${created.id}`);
    assert.equal(after.status, 404);
  });
});
