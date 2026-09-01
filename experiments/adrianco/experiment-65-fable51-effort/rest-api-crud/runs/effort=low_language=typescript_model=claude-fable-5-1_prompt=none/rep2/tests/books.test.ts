import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import { createApp } from "../src/app";
import { createDb, type Db } from "../src/db";

let db: Db;
let app: ReturnType<typeof createApp>;

beforeEach(() => {
  db = createDb(":memory:");
  app = createApp(db);
});

afterEach(() => db.close());

const sample = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441013593" };

describe("GET /health", () => {
  it("returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with Location header", async () => {
    const res = await request(app).post("/books").send(sample);
    expect(res.status).toBe(201);
    expect(res.headers.location).toBe(`/books/${res.body.id}`);
    expect(res.body).toMatchObject({ id: expect.any(Number), ...sample });
  });

  it("rejects missing title and author with 400", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toHaveLength(2);
    expect(res.body.errors.join(" ")).toMatch(/title/);
    expect(res.body.errors.join(" ")).toMatch(/author/);
  });

  it("rejects invalid year and isbn", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "X", author: "Y", year: "nineteen", isbn: "not-an-isbn" });
    expect(res.status).toBe(400);
    expect(res.body.errors).toHaveLength(2);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("{bad json");
    expect(res.status).toBe(400);
    expect(res.body.errors[0]).toMatch(/invalid JSON/);
  });
});

describe("GET /books", () => {
  it("lists all books and filters by author (case-insensitive)", async () => {
    await request(app).post("/books").send(sample);
    await request(app).post("/books").send({ title: "Neuromancer", author: "William Gibson" });
    await request(app).post("/books").send({ title: "Children of Dune", author: "Frank Herbert" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(3);

    const filtered = await request(app).get("/books").query({ author: "frank herbert" });
    expect(filtered.status).toBe(200);
    expect(filtered.body.map((b: { title: string }) => b.title)).toEqual(["Dune", "Children of Dune"]);

    const none = await request(app).get("/books").query({ author: "Nobody" });
    expect(none.body).toEqual([]);
  });

  it("rejects an empty author filter", async () => {
    const res = await request(app).get("/books?author=");
    expect(res.status).toBe(400);
  });
});

describe("GET /books/:id", () => {
  it("returns the book or 404", async () => {
    const created = await request(app).post("/books").send(sample);
    const ok = await request(app).get(`/books/${created.body.id}`);
    expect(ok.status).toBe(200);
    expect(ok.body).toEqual(created.body);

    const missing = await request(app).get("/books/9999");
    expect(missing.status).toBe(404);

    const bad = await request(app).get("/books/abc");
    expect(bad.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      id: created.body.id,
      title: "Dune Messiah",
      author: "Frank Herbert",
      year: 1969,
      isbn: null,
    });
  });

  it("returns 404 for unknown id and 400 for invalid body", async () => {
    const missing = await request(app).put("/books/42").send(sample);
    expect(missing.status).toBe(404);

    const created = await request(app).post("/books").send(sample);
    const invalid = await request(app).put(`/books/${created.body.id}`).send({ title: "" });
    expect(invalid.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204, then 404", async () => {
    const created = await request(app).post("/books").send(sample);
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const again = await request(app).delete(`/books/${created.body.id}`);
    expect(again.status).toBe(404);

    const get = await request(app).get(`/books/${created.body.id}`);
    expect(get.status).toBe(404);
  });
});
