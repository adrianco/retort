# Architecture Summary — book-api (Go / Gin / SQLite)

## Surface
A single-binary REST API for a book collection: CRUD over `/books`, an
`?author=` list filter, and a `/health` check. Data persists in a local
SQLite file.

## Modules
- **app.go** (244 LoC) — the whole service:
  - `Book` / `BookInput` / `ErrorResponse` model structs.
  - `initDB()` — opens `./books.db`, creates the `books` table (`title`/`author` NOT NULL).
  - Handlers: `healthHandler`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`.
  - `main()` — wires routes on a `gin.Default()` engine, listens on `:8080`.
- **app_test.go** (343 LoC) — 12 table-free httptest handler tests against a
  `test_books.db` fixture (`setupTestDB` + `TestMain`).

## Interfaces
| Route | Handler | Codes |
|-------|---------|-------|
| POST /books | createBook | 201, 400 |
| GET /books(?author=) | listBooks | 200, 500 |
| GET /books/:id | getBook | 200, 400, 404 |
| PUT /books/:id | updateBook | 200, 400, 404 |
| DELETE /books/:id | deleteBook | 200, 400, 404 |
| GET /health | healthHandler | 200 |

## Flow
Request → gin router → handler → `database/sql` prepared query against SQLite →
JSON response. Global `db *sql.DB` shared by handlers; tests swap it for a
throwaway file DB. No service/repository layering — handlers embed SQL directly,
which is idiomatic for a task this size.
