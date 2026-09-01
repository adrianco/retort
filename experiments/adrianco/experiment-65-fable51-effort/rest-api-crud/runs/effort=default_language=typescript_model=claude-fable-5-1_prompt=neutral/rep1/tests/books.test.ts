import { afterAll, beforeEach, describe, expect, it } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { BookRepository, openDatabase } from "../src/db.js";

const db = openDatabase(":memory:");
const app = createApp(db);
const repo = new BookRepository(db);

const dune = { title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441013593" };
const hobbit = { title: "The Hobbit", author: "J.R.R. Tolkien", year: 1937, isbn: "0-306-40615-2" };

beforeEach(() => repo.clear());
afterAll(() => db.close());

describe("GET /health", () => {
  it("reports ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok", database: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with a Location header", async () => {
    const res = await request(app).post("/books").send(dune);
    expect(res.status).toBe(201);
    expect(res.headers.location).toBe(`/books/${res.body.id}`);
    expect(res.body).toMatchObject({ ...dune, isbn: "9780441013593", id: expect.any(Number) });
    expect(res.body.createdAt).toEqual(expect.any(String));
  });

  it("allows year and isbn to be omitted", async () => {
    const res = await request(app).post("/books").send({ title: "Untitled", author: "Anon" });
    expect(res.status).toBe(201);
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it("rejects a missing title and author with 400 and field details", async () => {
    const res = await request(app).post("/books").send({ year: 2000 });
    expect(res.status).toBe(400);
    const fields = res.body.details.map((d: { field: string }) => d.field);
    expect(fields).toEqual(expect.arrayContaining(["title", "author"]));
  });

  it("rejects blank strings, non-integer years and bad ISBNs", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "   ", author: 42, year: "1999", isbn: "not-an-isbn" });
    expect(res.status).toBe(400);
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["author", "isbn", "title", "year"]);
  });

  it("rejects malformed JSON with 400", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send('{"title": ');
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/Malformed JSON/);
  });

  it("rejects a duplicate ISBN with 409", async () => {
    await request(app).post("/books").send(dune).expect(201);
    const res = await request(app).post("/books").send({ ...dune, title: "Dune (reprint)" });
    expect(res.status).toBe(409);
  });

  it("treats differently formatted ISBNs as the same book", async () => {
    await request(app).post("/books").send(dune).expect(201);
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune (reprint)", author: "Frank Herbert", isbn: "9780441013593" });
    expect(res.status).toBe(409);
  });
});

describe("GET /books", () => {
  it("returns an empty list initially", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("lists all books and filters by ?author= case-insensitively", async () => {
    await request(app).post("/books").send(dune).expect(201);
    await request(app).post("/books").send(hobbit).expect(201);
    await request(app)
      .post("/books")
      .send({ title: "Children of Dune", author: "Frank Herbert", year: 1976 })
      .expect(201);

    const all = await request(app).get("/books");
    expect(all.body).toHaveLength(3);

    const herbert = await request(app).get("/books").query({ author: "frank herbert" });
    expect(herbert.status).toBe(200);
    expect(herbert.body.map((b: { title: string }) => b.title)).toEqual([
      "Dune",
      "Children of Dune",
    ]);

    const nobody = await request(app).get("/books").query({ author: "Nobody" });
    expect(nobody.body).toEqual([]);
  });

  it("rejects a repeated author filter", async () => {
    const res = await request(app).get("/books?author=a&author=b");
    expect(res.status).toBe(400);
  });
});

describe("GET /books/:id", () => {
  it("returns the book", async () => {
    const created = await request(app).post("/books").send(hobbit);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body).toEqual(created.body);
  });

  it("returns 404 for an unknown id and 400 for a non-numeric id", async () => {
    expect((await request(app).get("/books/999")).status).toBe(404);
    expect((await request(app).get("/books/abc")).status).toBe(400);
    expect((await request(app).get("/books/0")).status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("replaces the book and bumps updatedAt", async () => {
    const created = await request(app).post("/books").send(dune);
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Dune Messiah", author: "Frank Herbert", year: 1969 });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: "Dune Messiah",
      year: 1969,
      isbn: null,
    });
    expect(res.body.createdAt).toBe(created.body.createdAt);

    const fetched = await request(app).get(`/books/${created.body.id}`);
    expect(fetched.body.title).toBe("Dune Messiah");
  });

  it("validates the body and returns 404 for an unknown id", async () => {
    const created = await request(app).post("/books").send(dune);
    const bad = await request(app).put(`/books/${created.body.id}`).send({ title: "No author" });
    expect(bad.status).toBe(400);

    const missing = await request(app).put("/books/12345").send(hobbit);
    expect(missing.status).toBe(404);
  });

  it("returns 409 when the new ISBN belongs to another book", async () => {
    await request(app).post("/books").send(dune).expect(201);
    const other = await request(app).post("/books").send(hobbit).expect(201);
    const res = await request(app)
      .put(`/books/${other.body.id}`)
      .send({ ...hobbit, isbn: dune.isbn });
    expect(res.status).toBe(409);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes the book and returns 204, then 404", async () => {
    const created = await request(app).post("/books").send(dune);
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);
    expect(del.text).toBe("");

    expect((await request(app).get(`/books/${created.body.id}`)).status).toBe(404);
    expect((await request(app).delete(`/books/${created.body.id}`)).status).toBe(404);
  });
});

describe("unknown routes", () => {
  it("returns a JSON 404", async () => {
    const res = await request(app).get("/nope");
    expect(res.status).toBe(404);
    expect(res.body).toEqual({ error: "Not found" });
  });
});
