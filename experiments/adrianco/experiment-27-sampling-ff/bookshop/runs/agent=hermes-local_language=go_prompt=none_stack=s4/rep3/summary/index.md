# Architecture Summary — book-api (Go / Gin / SQLite)

A single-package (`package main`) REST service. Two source files, no internal packages.

## Modules

| File | Role |
|------|------|
| `app.go` (278 LOC) | Everything: models, DB init, HTTP routing, and the 6 handlers. |
| `app_test.go` (364 LOC) | HTTP-level integration tests via `httptest`, against a throwaway `books_test.db`. |

## Data model

- `Book` — persisted entity (`id, title, author, year, isbn`).
- `CreateBookRequest` — POST body; `title`/`author` carry `binding:"required"`.
- `UpdateBookRequest` — PUT body; all fields optional (partial update).
- Storage: SQLite file `./books.db`, table `books` with `id INTEGER PRIMARY KEY AUTOINCREMENT`, `title`/`author` `NOT NULL`.

## Interfaces (routes)

`GET /health`, `POST /books`, `GET /books` (`?author=` filter), `GET /books/:id`, `PUT /books/:id`, `DELETE /books/:id`.

## Flow

`main()` → `initDB()` (open + `CREATE TABLE IF NOT EXISTS`) → register routes on `gin.Default()` → `r.Run(":8080")`. Handlers use the package-global `*sql.DB` (`db`) directly with parameterized queries. Errors map to 400/404/500; `/health` pings the DB and returns 503 on failure.

## Notes

- Global `db` is shared by app and tests; tests swap it to `books_test.db` via `setupTestDB()`.
- All SQL uses bound parameters (no injection surface).
- No pagination, auth, or migrations — not required by TASK.md.
