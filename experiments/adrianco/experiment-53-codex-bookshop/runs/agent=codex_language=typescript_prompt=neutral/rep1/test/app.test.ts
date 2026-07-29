import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import request from "supertest";
import { createApp } from "../src/app";
import { createDatabase } from "../src/db";

describe("books API", () => {
  let database: ReturnType<typeof createDatabase>;
  let app: ReturnType<typeof createApp>;

  afterEach(() => database.close());

  function setup() {
    database = createDatabase(":memory:");
    app = createApp(database);
  }

  it("reports health", async () => {
    setup();
    const response = await request(app).get("/health");
    assert.equal(response.status, 200);
    assert.deepEqual(response.body, { status: "ok" });
  });

  it("creates, lists with an author filter, and retrieves a book", async () => {
    setup();
    const created = await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "0441013597" });
    assert.equal(created.status, 201);
    assert.equal(created.body.title, "Dune");
    const filtered = await request(app).get("/books?author=Frank%20Herbert");
    assert.equal(filtered.status, 200);
    assert.equal(filtered.body.length, 1);
    const fetched = await request(app).get(`/books/${created.body.id}`);
    assert.deepEqual(fetched.body, created.body);
  });

  it("validates required fields and supports update/delete", async () => {
    setup();
    const invalid = await request(app).post("/books").send({ title: "Missing author" });
    assert.equal(invalid.status, 400);
    const created = await request(app).post("/books").send({ title: "Old", author: "Author" });
    const updated = await request(app).put(`/books/${created.body.id}`).send({ title: "New" });
    assert.equal(updated.status, 200);
    assert.equal(updated.body.title, "New");
    const deleted = await request(app).delete(`/books/${created.body.id}`);
    assert.equal(deleted.status, 204);
    assert.equal((await request(app).get(`/books/${created.body.id}`)).status, 404);
  });

  it("persists optional fields and returns 404 for unknown books", async () => {
    setup();
    const created = await request(app).post("/books").send({
      title: "The Left Hand of Darkness",
      author: "Ursula K. Le Guin",
      year: 1969,
      isbn: "0441478123",
    });
    assert.equal(created.status, 201);
    assert.deepEqual(created.body, {
      id: created.body.id,
      title: "The Left Hand of Darkness",
      author: "Ursula K. Le Guin",
      year: 1969,
      isbn: "0441478123",
    });
    assert.equal((await request(app).get("/books/999999")).status, 404);
  });

  it("rejects non-object JSON and invalid IDs", async () => {
    setup();
    const invalidBody = await request(app)
      .post("/books")
      .set("Content-Type", "application/json")
      .send("[]");
    assert.equal(invalidBody.status, 400);
    assert.equal((await request(app).get("/books/not-an-id")).status, 400);
  });
});
