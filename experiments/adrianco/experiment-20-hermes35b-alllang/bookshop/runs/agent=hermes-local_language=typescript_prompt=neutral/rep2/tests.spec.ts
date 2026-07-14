import request from "supertest";
import { app } from "./app";
import { closeDatabase, initializeDatabase } from "./db";

// Helper to reset the database between tests
async function resetDb() {
  closeDatabase();
  initializeDatabase(":memory:");
}

beforeEach(async () => {
  await resetDb();
});

afterAll(() => {
  closeDatabase();
});

describe("Health Check", () => {
  it("should return 200 with status ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("should create a new book with all fields", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "The Great Gatsby", author: "F. Scott Fitzgerald", year: 1925, isbn: "978-0743273565" });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty("id");
    expect(res.body.title).toBe("The Great Gatsby");
    expect(res.body.author).toBe("F. Scott Fitzgerald");
    expect(res.body.year).toBe(1925);
    expect(res.body.isbn).toBe("978-0743273565");
  });

  it("should create a book with minimal fields (no year/isbn)", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "1984", author: "George Orwell" });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe("1984");
    expect(res.body.author).toBe("George Orwell");
    expect(res.body.year).toBeNull();
    expect(res.body.isbn).toBeNull();
  });

  it("should return 400 when title is missing", async () => {
    const res = await request(app)
      .post("/books")
      .send({ author: "Someone" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
  });

  it("should return 400 when author is missing", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Some Book" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Validation failed");
  });
});

describe("GET /books", () => {
  it("should return empty list when no books exist", async () => {
    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("should return all books", async () => {
    await request(app).post("/books").send({ title: "Book A", author: "Author X" });
    await request(app).post("/books").send({ title: "Book B", author: "Author Y" });

    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(2);
  });

  it("should filter books by author", async () => {
    await request(app).post("/books").send({ title: "Book A", author: "Author X" });
    await request(app).post("/books").send({ title: "Book B", author: "Author X" });
    await request(app).post("/books").send({ title: "Book C", author: "Author Y" });

    const res = await request(app).get("/books?author=Author+X");
    expect(res.status).toBe(200);
    expect(res.body.length).toBe(2);
    expect(res.body.every((b: any) => b.author === "Author X")).toBe(true);
  });
});

describe("GET /books/:id", () => {
  it("should return a book by ID", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "To Kill a Mockingbird", author: "Harper Lee", year: 1960 });

    const bookId = res.body.id;

    const getRes = await request(app).get(`/books/${bookId}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.title).toBe("To Kill a Mockingbird");
  });

  it("should return 404 for non-existent book", async () => {
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
    expect(res.body.error).toBe("Book not found");
  });

  it("should return 400 for invalid ID", async () => {
    const res = await request(app).get("/books/abc");
    expect(res.status).toBe(400);
  });
});

describe("PUT /books/:id", () => {
  it("should update a book", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Original", author: "Original Author", year: 2000 });

    const bookId = res.body.id;

    const updateRes = await request(app)
      .put(`/books/${bookId}`)
      .send({ title: "Updated Title", year: 2020 });

    expect(updateRes.status).toBe(200);
    expect(updateRes.body.title).toBe("Updated Title");
    expect(updateRes.body.year).toBe(2020);
    expect(updateRes.body.author).toBe("Original Author");
  });

  it("should return 404 for non-existent book", async () => {
    const res = await request(app)
      .put("/books/9999")
      .send({ title: "Ghost" });

    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("should delete a book", async () => {
    const res = await request(app)
      .post("/books")
      .send({ title: "Temporary", author: "Temp Author" });

    const bookId = res.body.id;

    const deleteRes = await request(app).delete(`/books/${bookId}`);
    expect(deleteRes.status).toBe(204);

    // Verify it's gone
    const getRes = await request(app).get(`/books/${bookId}`);
    expect(getRes.status).toBe(404);
  });

  it("should return 404 for non-existent book", async () => {
    const res = await request(app).delete("/books/9999");
    expect(res.status).toBe(404);
  });
});

describe("Database persistence", () => {
  it("should persist data across requests in the same session", async () => {
    // Create a book
    await request(app).post("/books").send({
      title: "War and Peace",
      author: "Leo Tolstoy",
      year: 1869,
      isbn: "978-0199232765"
    });

    // List all books
    const listRes = await request(app).get("/books");
    expect(listRes.status).toBe(200);
    expect(listRes.body.length).toBe(1);
    expect(listRes.body[0].title).toBe("War and Peace");
  });
});
