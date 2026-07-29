import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import request from "supertest";
import { afterEach, describe, expect, it } from "vitest";
import { createApp } from "./app";

const resources: Array<{ app: ReturnType<typeof createApp>; dir: string }> = [];
afterEach(() => {
  for (const resource of resources.splice(0)) {
    resource.app.closeDatabase();
    rmSync(resource.dir, { recursive: true, force: true });
  }
});
function testApp() {
  const dir = mkdtempSync(join(tmpdir(), "books-api-"));
  const app = createApp(join(dir, "test.db"));
  resources.push({ app, dir });
  return app;
}

describe("books API", () => {
  it("reports health and validates required fields", async () => {
    const app = testApp();
    expect((await request(app).get("/health")).body).toEqual({ status: "ok" });
    expect((await request(app).post("/books").send({ author: "A" })).status).toBe(400);
  });

  it("creates, lists with an author filter, and fetches a book", async () => {
    const app = testApp();
    const created = await request(app).post("/books").send({ title: "Dune", author: "Frank Herbert", year: 1965, isbn: "x" });
    expect(created.status).toBe(201);
    expect(created.body.title).toBe("Dune");
    expect((await request(app).get("/books?author=Frank%20Herbert")).body).toHaveLength(1);
    expect((await request(app).get(`/books/${created.body.id}`)).status).toBe(200);
  });

  it("updates and deletes a book", async () => {
    const app = testApp();
    const created = await request(app).post("/books").send({ title: "Old", author: "Author" });
    const id = created.body.id;
    expect((await request(app).put(`/books/${id}`).send({ title: "New" })).body.title).toBe("New");
    expect((await request(app).delete(`/books/${id}`)).status).toBe(204);
    expect((await request(app).get(`/books/${id}`)).status).toBe(404);
  });

  it("persists books in SQLite when the app is recreated", async () => {
    const dir = mkdtempSync(join(tmpdir(), "books-api-persist-"));
    const databasePath = join(dir, "books.db");
    const firstApp = createApp(databasePath);
    const created = await request(firstApp).post("/books").send({ title: "Foundation", author: "Isaac Asimov", year: 1951 });
    firstApp.closeDatabase();

    const secondApp = createApp(databasePath);
    expect((await request(secondApp).get(`/books/${created.body.id}`)).body).toMatchObject({ title: "Foundation", author: "Isaac Asimov" });
    secondApp.closeDatabase();
    rmSync(dir, { recursive: true, force: true });
  });

  it("rejects malformed values and missing books", async () => {
    const app = testApp();
    expect((await request(app).post("/books").send({ title: "Book", author: "Author", year: "2020" })).status).toBe(400);
    expect((await request(app).get("/books/not-an-id")).status).toBe(400);
    expect((await request(app).get("/books/999999")).status).toBe(404);
  });
});
