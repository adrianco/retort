import request from "supertest";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { DatabaseSync } from "node:sqlite";
import { createApp } from "../src/app.js";
import { openDatabase } from "../src/db.js";

let db: DatabaseSync;
let app: ReturnType<typeof createApp>;

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441013593" };
const messiah = { title: "Dune Messiah", author: "Frank Herbert", year: 1969 };
const neuromancer = { title: "Neuromancer", author: "William Gibson", year: 1984, isbn: "0-441-56959-5" };

beforeEach(() => {
  db = openDatabase(":memory:");
  app = createApp(db);
});

afterEach(() => {
  db.close();
});

describe("GET /health", () => {
  it("returns ok with database status", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ status: "ok", database: "ok" });
    expect(typeof res.body.timestamp).toBe("string");
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with Location header", async () => {
    const res = await request(app).post("/books").send(dune);
    expect(res.status).toBe(201);
    expect(res.headers.location).toBe(`/books/${res.body.id}`);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: "Dune",
      author: "Frank Herbert",
      year: 1965,
      isbn: "9780441013593",
    });
    expect(res.body.createdAt).toBeTypeOf("string");
    expect(res.body.updatedAt).toBeTypeOf("string");
  });

  it("allows optional year and isbn to be omitted", async () => {
    const res = await request(app).post("/books").send({ title: "Untitled", author: "Anon" });
    expect(res.status).toBe(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it("rejects a missing title and author with 400 and field-level details", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation Error");
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["author", "title"]);
  });

  it("rejects blank strings for title and author", async () => {
    const res = await request(app).post("/books").send({ title: "   ", author: "" });
    expect(res.status).toBe(400);
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["author", "title"]);
  });

  it("rejects a non-integer year and an invalid isbn", async () => {
    const res = await request(app).post("/books").send({ title: "X", author: "Y", year: "nineteen", isbn: "abc" });
    expect(res.status).toBe(400);
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["isbn", "year"]);
  });

  it("rejects unknown fields", async () => {
    const res = await request(app).post("/books").send({ ...dune, publisher: "Chilton" });
    expect(res.status).toBe(400);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await request(app).post("/books").set("Content-Type", "application/json").send("{not json");
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Bad Request");
  });

  it("returns 409 when the isbn already exists", async () => {
    await request(app).post("/books").send(dune).expect(201);
    const res = await request(app).post("/books").send({ ...messiah, isbn: "9780441013593" });
    expect(res.status).toBe(409);
    expect(res.body.error).toBe("Conflict");
  });
});

describe("GET /books", () => {
  it("returns an empty list initially", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("lists all books in insertion order", async () => {
    await request(app).post("/books").send(dune);
    await request(app).post("/books").send(neuromancer);
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body.map((b: { title: string }) => b.title)).toEqual(["Dune", "Neuromancer"]);
  });

  it("filters by ?author= (case-insensitive exact match)", async () => {
    await request(app).post("/books").send(dune);
    await request(app).post("/books").send(messiah);
    await request(app).post("/books").send(neuromancer);

    const res = await request(app).get("/books").query({ author: "frank herbert" });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Frank Herbert")).toBe(true);

    const none = await request(app).get("/books").query({ author: "Nobody" });
    expect(none.status).toBe(200);
    expect(none.body).toEqual([]);
  });
});

describe("GET /books/:id", () => {
  it("returns the book", async () => {
    const created = await request(app).post("/books").send(dune);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body).toEqual(created.body);
  });

  it("returns 404 for an unknown id", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("Not Found");
  });

  it("returns 400 for a non-numeric id", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation Error");
  });
});

describe("PUT /books/:id", () => {
  it("replaces the book and bumps updatedAt", async () => {
    const created = await request(app).post("/books").send(dune);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Dune (Deluxe)", author: "Frank Herbert", year: 2019 });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: "Dune (Deluxe)",
      author: "Frank Herbert",
      year: 2019,
      isbn: null,
    });
    expect(res.body.createdAt).toBe(created.body.createdAt);
    expect(res.body.updatedAt >= created.body.updatedAt).toBe(true);

    const fetched = await request(app).get(`/books/${created.body.id}`);
    expect(fetched.body.title).toBe("Dune (Deluxe)");
  });

  it("validates the body on update", async () => {
    const created = await request(app).post("/books").send(dune);
    const res = await request(app).put(`/books/${created.body.id}`).send({ title: "Only title" });
    expect(res.status).toBe(400);
    expect(res.body.details[0].field).toBe("author");
  });

  it("returns 404 for an unknown id", async () => {
    const res = await request(app).put("/books/424242").send(dune);
    expect(res.status).toBe(404);
  });

  it("returns 409 when updating to an isbn owned by another book", async () => {
    await request(app).post("/books").send(dune);
    const other = await request(app).post("/books").send(neuromancer);
    const res = await request(app).put(`/books/${other.body.id}`).send({ ...neuromancer, isbn: "9780441013593" });
    expect(res.status).toBe(409);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes the book and returns 204", async () => {
    const created = await request(app).post("/books").send(dune);
    const res = await request(app).delete(`/books/${created.body.id}`);
    expect(res.status).toBe(204);
    expect(res.text).toBe("");

    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when deleting an unknown id", async () => {
    const res = await request(app).delete("/books/9999");
    expect(res.status).toBe(404);
  });
});

describe("unknown routes", () => {
  it("returns a JSON 404", async () => {
    const res = await request(app).get("/nope");
    expect(res.status).toBe(404);
    expect(res.body).toEqual({ error: "Not Found", message: "Route not found" });
  });
});
