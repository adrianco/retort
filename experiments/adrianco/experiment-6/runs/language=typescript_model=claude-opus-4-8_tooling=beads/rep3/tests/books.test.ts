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
  author: "Andy Hunt",
  year: 1999,
  isbn: "978-0201616224",
};

describe("GET /health", () => {
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

  it("rejects a book missing title and author with 400", async () => {
    const res = await request(app).post("/books").send({ year: 2020 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toEqual(
      expect.arrayContaining([
        expect.stringContaining("title"),
        expect.stringContaining("author"),
      ]),
    );
  });

  it("rejects a non-integer year with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "X", author: "Y", year: "soon" });
    expect(res.status).toBe(400);
  });

  it("allows optional year and isbn to be omitted", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Minimal", author: "Nobody" });
    expect(res.status).toBe(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });
});

describe("GET /books", () => {
  it("lists all books", async () => {
    await request(app).post("/books").send(sample);
    await request(app)
      .post("/books")
      .send({ title: "Clean Code", author: "Robert Martin" });
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it("filters by author", async () => {
    await request(app).post("/books").send(sample);
    await request(app)
      .post("/books")
      .send({ title: "Clean Code", author: "Robert Martin" });
    const res = await request(app).get("/books").query({ author: "Andy Hunt" });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe("Andy Hunt");
  });
});

describe("GET /books/:id", () => {
  it("returns a single book", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(created.body.id);
  });

  it("returns 404 for a missing book", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
  });

  it("returns 400 for a non-numeric id", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates an existing book", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ ...sample, title: "The Pragmatic Programmer (2nd ed.)" });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("The Pragmatic Programmer (2nd ed.)");
  });

  it("returns 404 when updating a missing book", async () => {
    const res = await request(app).put("/books/9999").send(sample);
    expect(res.status).toBe(404);
  });

  it("returns 400 on invalid update payload", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "" });
    expect(res.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes an existing book and returns 204", async () => {
    const created = await request(app).post("/books").send(sample);
    const res = await request(app).delete(`/books/${created.body.id}`);
    expect(res.status).toBe(204);
    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when deleting a missing book", async () => {
    const res = await request(app).delete("/books/9999");
    expect(res.status).toBe(404);
  });
});
