import request from "supertest";
import { createApp } from "../src/app";
import { createDb } from "../src/db";

function makeApp() {
  const db = createDb(":memory:");
  return createApp(db);
}

describe("GET /health", () => {
  it("returns 200 with status ok", async () => {
    const app = makeApp();
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});

describe("POST /books", () => {
  it("creates a book and returns 201", async () => {
    const app = makeApp();
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "978-0441013593" });
    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      id: expect.any(Number),
      title: "Dune",
      author: "Frank Herbert",
      year: 1965,
      isbn: "978-0441013593",
    });
  });

  it("returns 400 when title is missing", async () => {
    const app = makeApp();
    const res = await request(app)
      .post("/books")
      .send({ author: "Frank Herbert" });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/title/i);
  });

  it("returns 400 when author is missing", async () => {
    const app = makeApp();
    const res = await request(app)
      .post("/books")
      .send({ title: "Dune" });
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/author/i);
  });
});

describe("GET /books", () => {
  it("returns all books", async () => {
    const app = makeApp();
    await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Foundation", author: "Isaac Asimov" });

    const res = await request(app).get("/books");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it("filters by author", async () => {
    const app = makeApp();
    await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert" });
    await request(app).post("/books").send({ title: "Foundation", author: "Isaac Asimov" });

    const res = await request(app).get("/books?author=Asimov");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].author).toBe("Isaac Asimov");
  });
});

describe("GET /books/:id", () => {
  it("returns a single book", async () => {
    const app = makeApp();
    const created = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert" });

    const res = await request(app).get(`/books/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe("Dune");
  });

  it("returns 404 for unknown id", async () => {
    const app = makeApp();
    const res = await request(app).get("/books/9999");
    expect(res.status).toBe(404);
  });
});

describe("PUT /books/:id", () => {
  it("updates a book", async () => {
    const app = makeApp();
    const created = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert", year: 1965 });

    const res = await request(app)
      .put(`/books/${created.body.id}`)
      .send({ year: 1966 });
    expect(res.status).toBe(200);
    expect(res.body.year).toBe(1966);
    expect(res.body.title).toBe("Dune");
  });

  it("returns 404 for unknown id", async () => {
    const app = makeApp();
    const res = await request(app).put("/books/9999").send({ title: "X" });
    expect(res.status).toBe(404);
  });
});

describe("DELETE /books/:id", () => {
  it("deletes a book and returns 204", async () => {
    const app = makeApp();
    const created = await request(app)
      .post("/books")
      .send({ title: "Dune", author: "Frank Herbert" });

    const del = await request(app).delete(`/books/${created.body.id}`);
    expect(del.status).toBe(204);

    const get = await request(app).get(`/books/${created.body.id}`);
    expect(get.status).toBe(404);
  });

  it("returns 404 when book does not exist", async () => {
    const app = makeApp();
    const res = await request(app).delete("/books/9999");
    expect(res.status).toBe(404);
  });
});
