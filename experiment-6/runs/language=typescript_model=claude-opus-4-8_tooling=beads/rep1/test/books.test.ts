import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import type { Express } from "express";
import type Database from "better-sqlite3";
import { createApp } from "../src/app.js";
import { createDb } from "../src/db.js";

let db: Database.Database;
let app: Express;

beforeEach(() => {
  db = createDb(":memory:");
  app = createApp(db);
});

afterEach(() => {
  db.close();
});

const sample = {
  title: "The Pragmatic Programmer",
  author: "Andrew Hunt",
  year: 1999,
  isbn: "978-0201616224",
};

describe("health", () => {
  it("returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with an id", async () => {
    const res = await request(app).post("/books").send(sample);
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject(sample);
    expect(typeof res.body.id).toBe("number");
  });

  it("rejects a book missing required fields with 400", async () => {
    const res = await request(app).post("/books").send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toContain("title is required");
    expect(res.body.errors).toContain("author is required");
  });

  it("rejects a non-integer year with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "X", author: "Y", year: "soon" });
    expect(res.status).toBe(400);
    expect(res.body.errors).toContain("year must be an integer");
  });
});

describe("GET /books", () => {
  it("lists books and filters by author", async () => {
    await request(app).post("/books").send(sample);
    await request(app)
      .post("/books")
      .send({ title: "Clean Code", author: "Robert Martin" });

    const all = await request(app).get("/books");
    expect(all.status).toBe(200);
    expect(all.body).toHaveLength(2);

    const filtered = await request(app).get("/books?author=Andrew Hunt");
    expect(filtered.status).toBe(200);
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].author).toBe("Andrew Hunt");
  });
});

describe("GET /books/:id", () => {
  it("returns a single book", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(created.body.id);
  });

  it("returns 404 for an unknown id", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
  });
});

describe("PUT /books/:id", () => {
  it("updates an existing book", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ ...sample, year: 2019 });
    expect(res.status).toBe(200);
    expect(res.body.year).toBe(2019);
  });

  it("returns 404 when updating an unknown id", async () => {
    const res = await request(app).put("/books/9999").send(sample);
    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and then 404s", async () => {
    const created = await request(app).post("/books").send(sample);
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });
});
