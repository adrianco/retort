import { describe, it, expect, beforeEach, afterEach } from "vitest";
import request from "supertest";
import type { Express } from "express";
import type { DatabaseSync } from "node:sqlite";
import { createApp } from "../src/app.js";
import { createDatabase } from "../src/db.js";

/**
 * BDD-style integration tests for the Book Collection API.
 * Each test follows Given / When / Then and is named after an observable behaviour.
 */
describe("Book Collection API", () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    // Given: a fresh in-memory database and app for every scenario
    db = createDatabase(":memory:");
    app = createApp(db);
  });

  afterEach(() => {
    db.close();
  });

  describe("GET /health", () => {
    it("given the service is running when health is checked then it reports ok", async () => {
      // When
      const res = await request(app).get("/health");
      // Then
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: "ok" });
    });
  });

  describe("POST /books", () => {
    it("given a valid book when created then it returns 201 with an id", async () => {
      // Given
      const payload = {
        title: "The Pragmatic Programmer",
        author: "Andrew Hunt",
        year: 1999,
        isbn: "978-0201616224",
      };
      // When
      const res = await request(app).post("/books").send(payload);
      // Then
      expect(res.status).toBe(201);
      expect(res.body.id).toBeTypeOf("number");
      expect(res.body.title).toBe(payload.title);
    });

    it("given a missing title when created then it returns 400", async () => {
      // Given a body without a title
      const payload = { author: "Nobody" };
      // When
      const res = await request(app).post("/books").send(payload);
      // Then
      expect(res.status).toBe(400);
      expect(res.body.errors).toContain(
        "title is required and must be a non-empty string"
      );
    });

    it("given a missing author when created then it returns 400", async () => {
      // Given a body without an author
      const payload = { title: "Orphan Book" };
      // When
      const res = await request(app).post("/books").send(payload);
      // Then
      expect(res.status).toBe(400);
      expect(res.body.errors).toContain(
        "author is required and must be a non-empty string"
      );
    });
  });

  describe("GET /books", () => {
    it("given no books exist when listed then it returns an empty array", async () => {
      // When
      const res = await request(app).get("/books");
      // Then
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it("given books by different authors when filtered by author then only matches return", async () => {
      // Given two books by different authors
      await request(app)
        .post("/books")
        .send({ title: "Book A", author: "Alice" });
      await request(app).post("/books").send({ title: "Book B", author: "Bob" });
      // When filtering by Alice
      const res = await request(app).get("/books").query({ author: "Alice" });
      // Then
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(1);
      expect(res.body[0].author).toBe("Alice");
    });
  });

  describe("GET /books/:id", () => {
    it("given an existing book when fetched by id then it returns the book", async () => {
      // Given a created book
      const created = await request(app)
        .post("/books")
        .send({ title: "Clean Code", author: "Robert Martin" });
      // When
      const res = await request(app).get(`/books/${created.body.id}`);
      // Then
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("Clean Code");
    });

    it("given a non-existent id when fetched then it returns 404", async () => {
      // When
      const res = await request(app).get("/books/9999");
      // Then
      expect(res.status).toBe(404);
    });
  });

  describe("PUT /books/:id", () => {
    it("given an existing book when updated then it returns the updated book", async () => {
      // Given a created book
      const created = await request(app)
        .post("/books")
        .send({ title: "Old Title", author: "Author" });
      // When updating its title
      const res = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "New Title", author: "Author", year: 2020 });
      // Then
      expect(res.status).toBe(200);
      expect(res.body.title).toBe("New Title");
      expect(res.body.year).toBe(2020);
    });

    it("given a non-existent id when updated then it returns 404", async () => {
      // When
      const res = await request(app)
        .put("/books/9999")
        .send({ title: "X", author: "Y" });
      // Then
      expect(res.status).toBe(404);
    });
  });

  describe("DELETE /books/:id", () => {
    it("given an existing book when deleted then it returns 204 and is gone", async () => {
      // Given a created book
      const created = await request(app)
        .post("/books")
        .send({ title: "To Delete", author: "Author" });
      // When deleting it
      const del = await request(app).delete(`/books/${created.body.id}`);
      // Then it is removed
      expect(del.status).toBe(204);
      const fetch = await request(app).get(`/books/${created.body.id}`);
      expect(fetch.status).toBe(404);
    });

    it("given a non-existent id when deleted then it returns 404", async () => {
      // When
      const res = await request(app).delete("/books/9999");
      // Then
      expect(res.status).toBe(404);
    });
  });
});
