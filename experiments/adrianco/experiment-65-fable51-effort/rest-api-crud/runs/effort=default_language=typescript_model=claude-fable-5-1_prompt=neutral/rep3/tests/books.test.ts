import { afterEach, beforeEach, describe, expect, it } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { BookRepository } from "../src/db.js";

let repo: BookRepository;
let app: ReturnType<typeof createApp>;

const sampleBook = {
  title: "The Pragmatic Programmer",
  author: "David Thomas",
  year: 1999,
  isbn: "978-0-201-61622-4",
};

beforeEach(() => {
  repo = new BookRepository(":memory:");
  app = createApp(repo);
});

afterEach(() => {
  repo.close();
});

describe("GET /health", () => {
  it("reports ok when the database is reachable", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
    expect(res.body.database).toBe("ok");
    expect(typeof res.body.uptime).toBe("number");
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201 with the stored record", async () => {
    const res = await request(app).post("/books").send(sampleBook);
    expect(res.status).toBe(201);
    expect(res.headers.location).toBe(`/books/${res.body.id}`);
    expect(res.body).toMatchObject(sampleBook);
    expect(res.body.id).toBeTypeOf("number");
    expect(res.body.created_at).toBeTypeOf("string");
    expect(res.body.updated_at).toBeTypeOf("string");
  });

  it("trims whitespace and stores optional fields as null when omitted", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "  Dune  ", author: "  Frank Herbert " });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe("Dune");
    expect(res.body.author).toBe("Frank Herbert");
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it("rejects a payload missing title and author with field-level errors", async () => {
    const res = await request(app).post("/books").send({ year: 2001 });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["author", "title"]);
  });

  it("rejects blank strings, non-integer years and malformed ISBNs", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "   ", author: 42, year: "1999", isbn: "not-an-isbn" });
    expect(res.status).toBe(400);
    const fields = res.body.details.map((d: { field: string }) => d.field).sort();
    expect(fields).toEqual(["author", "isbn", "title", "year"]);
  });

  it("returns 400 for malformed JSON", async () => {
    const res = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("{not json");
    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Malformed JSON body");
  });

  it("returns 400 when the body is a JSON array instead of an object", async () => {
    const res = await request(app).post("/books").send([sampleBook]);
    expect(res.status).toBe(400);
    expect(res.body.details[0].field).toBe("body");
  });
});

describe("GET /books", () => {
  it("returns an empty list initially", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("lists all books in insertion order", async () => {
    await request(app).post("/books").send({ title: "A", author: "X" });
    await request(app).post("/books").send({ title: "B", author: "Y" });
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body.map((b: { title: string }) => b.title)).toEqual(["A", "B"]);
  });

  it("filters by author (case-insensitive exact match)", async () => {
    await request(app).post("/books").send({ title: "Emma", author: "Jane Austen" });
    await request(app).post("/books").send({ title: "Persuasion", author: "Jane Austen" });
    await request(app).post("/books").send({ title: "Dracula", author: "Bram Stoker" });

    const res = await request(app).get("/books").query({ author: "jane austen" });
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.every((b: { author: string }) => b.author === "Jane Austen")).toBe(true);

    const none = await request(app).get("/books").query({ author: "Nobody" });
    expect(none.status).toBe(200);
    expect(none.body).toEqual([]);
  });

  it("rejects a repeated author query parameter", async () => {
    const res = await request(app).get("/books?author=a&author=b");
    expect(res.status).toBe(400);
  });
});

describe("GET /books/:id", () => {
  it("returns the book when it exists", async () => {
    const created = await request(app).post("/books").send(sampleBook);
    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body).toEqual(created.body);
  });

  it("returns 404 for an unknown id", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
    expect(res.body.error).toMatch(/not found/i);
  });

  it("returns 400 for a non-numeric id", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("replaces the book and bumps updated_at", async () => {
    const created = await request(app).post("/books").send(sampleBook);
    await new Promise((r) => setTimeout(r, 5));
    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ title: "Updated Title", author: "New Author", year: 2020 });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({
      id: created.body.id,
      title: "Updated Title",
      author: "New Author",
      year: 2020,
      isbn: null,
    });
    expect(res.body.created_at).toBe(created.body.created_at);
    expect(res.body.updated_at >= created.body.updated_at).toBe(true);

    const fetched = await request(app).get(`/books/${created.body.id}`);
    expect(fetched.body.title).toBe("Updated Title");
  });

  it("validates the payload before touching the database", async () => {
    const created = await request(app).post("/books").send(sampleBook);
    const res = await request(app).put(`/books/${created.body.id}`).send({ title: "Only title" });
    expect(res.status).toBe(400);
    expect(res.body.details[0].field).toBe("author");

    const unchanged = await request(app).get(`/books/${created.body.id}`);
    expect(unchanged.body.title).toBe(sampleBook.title);
  });

  it("returns 404 when updating a missing book", async () => {
    const res = await request(app).put("/books/424242").send(sampleBook);
    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes an existing book and returns 204", async () => {
    const created = await request(app).post("/books").send(sampleBook);
    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);
    expect(del.text).toBe("");

    const after = await request(app).get(`/books/${created.body.id}`);
    expect(after.status).toBe(404);
  });

  it("returns 404 when the book does not exist", async () => {
    const res = await request(app).delete("/books/123456");
    expect(res.status).toBe(404);
  });
});

describe("unknown routes", () => {
  it("returns a JSON 404", async () => {
    const res = await request(app).get("/nope");
    expect(res.status).toBe(404);
    expect(res.body).toEqual({ error: "Not found" });
  });
});
