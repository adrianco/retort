import { beforeEach, describe, expect, it } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { BookRepository } from "../src/db.js";
import { validateBook } from "../src/validate.js";

let app: ReturnType<typeof createApp>;
const sample = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "9780441013593" };

beforeEach(() => {
  app = createApp(new BookRepository(":memory:"));
});

describe("validateBook", () => {
  it("requires title and author", () => {
    const r = validateBook({ year: 2000 });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors).toHaveLength(2);
  });
  it("rejects non-integer year", () => {
    expect(validateBook({ title: "a", author: "b", year: "x" }).ok).toBe(false);
  });
});

describe("Books API", () => {
  it("GET /health", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  it("creates and fetches a book", async () => {
    const created = await request(app).post("/books").send(sample);
    expect(created.status).toBe(201);
    expect(created.body).toMatchObject({ id: 1, ...sample });
    const got = await request(app).get(`/books/${created.body.id}`);
    expect(got.status).toBe(200);
    expect(got.body).toEqual(created.body);
  });

  it("returns 400 when title/author missing", async () => {
    const res = await request(app).post("/books").send({ year: 1999 });
    expect(res.status).toBe(400);
    expect(res.body.errors.length).toBe(2);
  });

  it("returns 400 on malformed JSON", async () => {
    const res = await request(app).post("/books").set("Content-Type", "application/json").send("{bad");
    expect(res.status).toBe(400);
  });

  it("lists books with author filter", async () => {
    await request(app).post("/books").send(sample);
    await request(app).post("/books").send({ title: "Emma", author: "Jane Austen" });
    expect((await request(app).get("/books")).body).toHaveLength(2);
    const filtered = await request(app).get("/books").query({ author: "Jane Austen" });
    expect(filtered.body).toHaveLength(1);
    expect(filtered.body[0].title).toBe("Emma");
  });

  it("updates a book", async () => {
    const { body } = await request(app).post("/books").send(sample);
    const res = await request(app).put(`/books/${body.id}`).send({ ...sample, title: "Dune Messiah", year: 1969 });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ title: "Dune Messiah", year: 1969 });
    expect((await request(app).put("/books/99").send(sample)).status).toBe(404);
    expect((await request(app).put(`/books/${body.id}`).send({ title: "" })).status).toBe(400);
  });

  it("deletes a book", async () => {
    const { body } = await request(app).post("/books").send(sample);
    expect((await request(app).delete(`/books/${body.id}`)).status).toBe(204);
    expect((await request(app).get(`/books/${body.id}`)).status).toBe(404);
    expect((await request(app).delete(`/books/${body.id}`)).status).toBe(404);
  });

  it("returns 400 for invalid id", async () => {
    expect((await request(app).get("/books/abc")).status).toBe(400);
  });
});
