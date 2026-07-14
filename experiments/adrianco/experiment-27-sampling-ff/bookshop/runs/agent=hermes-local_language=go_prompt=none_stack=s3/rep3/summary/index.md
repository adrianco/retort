# Architecture Summary

> The `run-summary` skill is not registered as an invocable skill in this
> environment; this summary was authored directly. Codebase is a single-package
> Go service, so the architecture is small enough to describe inline.

## Modules

- **`app.go`** (303 lines) — the entire service, `package main`.
  - **Data model:** `Book`, `CreateBookRequest`, `UpdateBookRequest` structs with JSON tags.
  - **Persistence:** package-level `*sql.DB` (`db`). `initDB()` → `initDBWithPath("./books.db")`; `initDBWithPath` opens go-sqlite3 and `CREATE TABLE IF NOT EXISTS books` (id AUTOINCREMENT, title/author NOT NULL, isbn UNIQUE).
  - **Handlers (Gin):** `healthCheck`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`.
  - **Routing:** `setupRouter()` wires `GET /health`, `POST/GET /books`, `GET/PUT/DELETE /books/:id`.
  - **Entrypoint:** `main()` initializes the DB, builds the router, and serves on `$PORT` (default 8080).
- **`app_test.go`** (438 lines) — 9 table-free `httptest` tests exercising every route via an in-memory (`:memory:`) DB through `setupTestRouter`.
- **`README.md`** — setup/run instructions and curl-based API docs.
- **`go.mod` / `go.sum`** — Gin + go-sqlite3.

## Request flow

`HTTP → Gin router (setupRouter) → handler → database/sql query against SQLite → gin.JSON response`.
Handlers validate input (title/author required) before the DB write, and return
404 on missing rows for get/update/delete.

## Interfaces

- REST/JSON over HTTP. No internal packages or exported library API — a self-contained binary.
- The only injectable seam is `initDBWithPath`, used by tests to swap in `:memory:`.
