import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { Server } from "node:http";
import type { Express } from "express";
import { createApp } from "../src/app.js";

let app: Express;
let server: Server;
let base: string;

function postBook(body: unknown, raw?: string) {
  return fetch(`${base}/books`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: raw ?? JSON.stringify(body),
  });
}

beforeAll(async () => {
  app = createApp(":memory:");
  await new Promise<void>((resolve) => {
    server = app.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address();
  if (address === null || typeof address === "string") {
    throw new Error("Unexpected server address");
  }
  base = `http://127.0.0.1:${address.port}`;
});

afterAll(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((err) => (err ? reject(err) : resolve()))
  );
});

describe("GET /health", () => {
  it("returns 200 with status ok", async () => {
    const res = await fetch(`${base}/health`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the stored book", async () => {
    const res = await postBook({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0547928227",
    });
    expect(res.status).toBe(201);
    const book = await res.json();
    expect(book).toMatchObject({
      title: "The Hobbit",
      author: "J.R.R. Tolkien",
      year: 1937,
      isbn: "978-0547928227",
    });
    expect(typeof book.id).toBe("number");
  });

  it("allows year and isbn to be omitted", async () => {
    const res = await postBook({ title: "No Metadata", author: "Someone" });
    expect(res.status).toBe(201);
    const book = await res.json();
    expect(book.year).toBeNull();
    expect(book.isbn).toBeNull();
  });

  it("rejects a missing title with 400", async () => {
    const res = await postBook({ author: "Only Author" });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/title/);
  });

  it("rejects a missing author with 400", async () => {
    const res = await postBook({ title: "Only Title" });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/author/);
  });

  it("rejects an empty-string title with 400", async () => {
    const res = await postBook({ title: "   ", author: "X" });
    expect(res.status).toBe(400);
  });

  it("rejects a non-integer year with 400", async () => {
    const res = await postBook({ title: "Bad Year", author: "X", year: "1999" });
    expect(res.status).toBe(400);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await postBook(null, "{not json");
    expect(res.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("lists all books", async () => {
    const res = await fetch(`${base}/books`);
    expect(res.status).toBe(200);
    const books = await res.json();
    expect(Array.isArray(books)).toBe(true);
    expect(books.length).toBeGreaterThanOrEqual(2);
    expect(books.some((b: { title: string }) => b.title === "The Hobbit")).toBe(true);
  });

  it("filters by ?author=", async () => {
    const res = await fetch(`${base}/books?author=J.R.R.%20Tolkien`);
    expect(res.status).toBe(200);
    const books = await res.json();
    expect(books.length).toBe(1);
    expect(books[0].title).toBe("The Hobbit");
  });

  it("returns an empty list for an unknown author", async () => {
    const res = await fetch(`${base}/books?author=No Such Author`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual([]);
  });
});

describe("GET /books/:id", () => {
  it("returns a single book by id", async () => {
    const created = await (
      await postBook({ title: "ById", author: "A" })
    ).json();
    const res = await fetch(`${base}/books/${created.id}`);
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ title: "ById", author: "A" });
  });

  it("returns 404 for a nonexistent id", async () => {
    const res = await fetch(`${base}/books/999999`);
    expect(res.status).toBe(404);
  });

  it("returns 400 for a malformed id", async () => {
    const res = await fetch(`${base}/books/not-a-number`);
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates provided fields and returns the updated book", async () => {
    const created = await (
      await postBook({ title: "Original", author: "Orig Author", year: 2000 })
    ).json();
    const res = await fetch(`${base}/books/${created.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "Updated", year: 2020 }),
    });
    expect(res.status).toBe(200);
    const book = await res.json();
    expect(book).toMatchObject({
      id: created.id,
      title: "Updated",
      author: "Orig Author", // untouched
      year: 2020,
    });
  });

  it("rejects an empty title with 400", async () => {
    const created = await (await postBook({ title: "T", author: "A" })).json();
    const res = await fetch(`${base}/books/${created.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects an empty body with 400", async () => {
    const created = await (await postBook({ title: "T", author: "A" })).json();
    const res = await fetch(`${base}/books/${created.id}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });

  it("returns 404 for a nonexistent id", async () => {
    const res = await fetch(`${base}/books/999999`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: "Ghost" }),
    });
    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book (204) and it is gone afterwards", async () => {
    const created = await (
      await postBook({ title: "Doomed", author: "Doomed Author" })
    ).json();
    const del = await fetch(`${base}/books/${created.id}`, { method: "DELETE" });
    expect(del.status).toBe(204);

    const get = await fetch(`${base}/books/${created.id}`);
    expect(get.status).toBe(404);
  });

  it("returns 404 when deleting a nonexistent id", async () => {
    const res = await fetch(`${base}/books/999999`, { method: "DELETE" });
    expect(res.status).toBe(404);
  });
});

describe("unknown routes", () => {
  it("returns a JSON 404", async () => {
    const res = await fetch(`${base}/nope`);
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: "Not found" });
  });
});
