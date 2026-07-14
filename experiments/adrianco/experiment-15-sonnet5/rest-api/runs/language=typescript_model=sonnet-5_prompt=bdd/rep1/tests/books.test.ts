import request from "supertest";
import { Express } from "express";
import { DatabaseSync } from "node:sqlite";
import { createApp } from "../src/app";
import { createDatabase } from "../src/db";

describe("Book collection API", () => {
  let db: DatabaseSync;
  let app: Express;

  beforeEach(() => {
    // Given a fresh in-memory database and app for every scenario
    db = createDatabase(":memory:");
    app = createApp(db);
  });

  afterEach(() => {
    db.close();
  });

  describe("GET /health", () => {
    test("given the service is running, when health is checked, then it reports ok", async () => {
      // When
      const response = await request(app).get("/health");

      // Then
      expect(response.status).toBe(200);
      expect(response.body).toEqual({ status: "ok" });
    });
  });

  describe("POST /books", () => {
    test("given valid book data, when creating a book, then it is persisted and returned with an id", async () => {
      // Given
      const newBook = {
        title: "The Pragmatic Programmer",
        author: "David Thomas",
        year: 1999,
        isbn: "978-0135957059",
      };

      // When
      const response = await request(app).post("/books").send(newBook);

      // Then
      expect(response.status).toBe(201);
      expect(response.body).toMatchObject(newBook);
      expect(response.body.id).toBeDefined();
    });

    test("given a missing title, when creating a book, then it is rejected with 400", async () => {
      // Given
      const invalidBook = { author: "David Thomas" };

      // When
      const response = await request(app).post("/books").send(invalidBook);

      // Then
      expect(response.status).toBe(400);
      expect(response.body.errors).toContain(
        "title is required and must be a non-empty string"
      );
    });

    test("given a missing author, when creating a book, then it is rejected with 400", async () => {
      // Given
      const invalidBook = { title: "The Pragmatic Programmer" };

      // When
      const response = await request(app).post("/books").send(invalidBook);

      // Then
      expect(response.status).toBe(400);
      expect(response.body.errors).toContain(
        "author is required and must be a non-empty string"
      );
    });
  });

  describe("GET /books", () => {
    test("given no books exist, when listing books, then an empty list is returned", async () => {
      // When
      const response = await request(app).get("/books");

      // Then
      expect(response.status).toBe(200);
      expect(response.body).toEqual([]);
    });

    test("given multiple books by different authors, when listing all books, then all are returned", async () => {
      // Given
      await request(app)
        .post("/books")
        .send({ title: "Book A", author: "Author One" });
      await request(app)
        .post("/books")
        .send({ title: "Book B", author: "Author Two" });

      // When
      const response = await request(app).get("/books");

      // Then
      expect(response.status).toBe(200);
      expect(response.body).toHaveLength(2);
    });

    test("given books by different authors, when filtering by author, then only matching books are returned", async () => {
      // Given
      await request(app)
        .post("/books")
        .send({ title: "Book A", author: "Author One" });
      await request(app)
        .post("/books")
        .send({ title: "Book B", author: "Author Two" });

      // When
      const response = await request(app).get("/books").query({ author: "Author One" });

      // Then
      expect(response.status).toBe(200);
      expect(response.body).toHaveLength(1);
      expect(response.body[0].author).toBe("Author One");
    });
  });

  describe("GET /books/:id", () => {
    test("given an existing book, when fetching it by id, then it is returned", async () => {
      // Given
      const created = await request(app)
        .post("/books")
        .send({ title: "Book A", author: "Author One" });

      // When
      const response = await request(app).get(`/books/${created.body.id}`);

      // Then
      expect(response.status).toBe(200);
      expect(response.body.title).toBe("Book A");
    });

    test("given no book with the given id, when fetching it, then 404 is returned", async () => {
      // When
      const response = await request(app).get("/books/999999");

      // Then
      expect(response.status).toBe(404);
    });
  });

  describe("PUT /books/:id", () => {
    test("given an existing book, when updating its title, then the change is persisted", async () => {
      // Given
      const created = await request(app)
        .post("/books")
        .send({ title: "Old Title", author: "Author One" });

      // When
      const response = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "New Title" });

      // Then
      expect(response.status).toBe(200);
      expect(response.body.title).toBe("New Title");
      expect(response.body.author).toBe("Author One");
    });

    test("given no book with the given id, when updating it, then 404 is returned", async () => {
      // When
      const response = await request(app)
        .put("/books/999999")
        .send({ title: "New Title" });

      // Then
      expect(response.status).toBe(404);
    });

    test("given an existing book, when updating with an empty title, then it is rejected with 400", async () => {
      // Given
      const created = await request(app)
        .post("/books")
        .send({ title: "Old Title", author: "Author One" });

      // When
      const response = await request(app)
        .put(`/books/${created.body.id}`)
        .send({ title: "" });

      // Then
      expect(response.status).toBe(400);
    });
  });

  describe("DELETE /books/:id", () => {
    test("given an existing book, when deleting it, then it is removed and no longer retrievable", async () => {
      // Given
      const created = await request(app)
        .post("/books")
        .send({ title: "Book A", author: "Author One" });

      // When
      const deleteResponse = await request(app).delete(`/books/${created.body.id}`);

      // Then
      expect(deleteResponse.status).toBe(204);
      const getResponse = await request(app).get(`/books/${created.body.id}`);
      expect(getResponse.status).toBe(404);
    });

    test("given no book with the given id, when deleting it, then 404 is returned", async () => {
      // When
      const response = await request(app).delete("/books/999999");

      // Then
      expect(response.status).toBe(404);
    });
  });
});
