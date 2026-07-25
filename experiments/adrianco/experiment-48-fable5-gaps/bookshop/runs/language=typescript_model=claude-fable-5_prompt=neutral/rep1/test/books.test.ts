import { beforeEach, describe, expect, it } from "vitest";
import request from "supertest";
import type { Express } from "express";
import { createApp } from "../src/app.js";
import { createDb } from "../src/db.js";

let app: Express;

beforeEach(() => {
  app = createApp(createDb(":memory:"));
});

describe("GET /health", () => {
  it("returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the stored record", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Release It!", author: "Michael Nygard", year: 2018, isbn: "978-1680502398" });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: 1,
      title: "Release It!",
      author: "Michael Nygard",
      year: 2018,
      isbn: "978-1680502398",
    });
  });

  it("accepts optional fields as missing", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Sun Performance and Tuning", author: "Adrian Cockcroft" });
    expect(res.status).toBe(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it("rejects missing title and author with 400", async () => {
    const res = await request(app).post("/books").send({ year: 1999 });
    expect(res.status).toBe(400);
    expect(res.body.errors).toHaveLength(2);
    expect(res.body.errors.join(" ")).toContain("title");
    expect(res.body.errors.join(" ")).toContain("author");
  });

  it("rejects blank title with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "   ", author: "Someone" });
    expect(res.status).toBe(400);
  });

  it("rejects non-integer year with 400", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "T", author: "A", year: "not a year" });
    expect(res.status).toBe(400);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("{not json");
    expect(res.status).toBe(400);
  });
});

describe("GET /books", () => {
  it("lists all books", async () => {
    await request(app).post("/books").send({ title: "A", author: "X" });
    await request(app).post("/books").send({ title: "B", author: "Y" });
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.map((b: { title: string }) => b.title)).toEqual(["A", "B"]);
  });

  it("filters by author", async () => {
    await request(app).post("/books").send({ title: "A", author: "X" });
    await request(app).post("/books").send({ title: "B", author: "Y" });
    await request(app).post("/books").send({ title: "C", author: "X" });
    const res = await request(app).get("/books").query({ author: "X" });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "X")).toBe(true);
  });

  it("returns an empty list when no books exist", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe("GET /books/:id", () => {
  it("returns the book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "A", author: "X" });
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ title: "A", author: "X" });
  });

  it("returns 404 for a missing book", async () => {
    const res = await request(app).get("/books/999");
    expect(res.status).toBe(404);
  });

  it("returns 400 for a non-numeric id", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Old", author: "X", year: 2000 });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "New", author: "Y", year: 2020, isbn: "123" });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: "New",
      author: "Y",
      year: 2020,
      isbn: "123",
    });
  });

  it("returns 404 when updating a missing book", async () => {
    const res = await request(app)
      .put("/books/999")
      .send({ title: "New", author: "Y" });
    expect(res.status).toBe(404);
  });

  it("rejects invalid update payload with 400", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "Old", author: "X" });
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "" });
    expect(res.status).toBe(400);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204", async () => {
    const created = await request(app)
      .post("/books")
      .send({ title: "A", author: "X" });
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);
    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when deleting a missing book", async () => {
    const res = await request(app).delete("/books/999");
    expect(res.status).toBe(404);
  });
});
