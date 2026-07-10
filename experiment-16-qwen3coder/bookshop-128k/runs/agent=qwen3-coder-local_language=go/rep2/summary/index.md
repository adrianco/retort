# Architecture Summary

Single-package Go HTTP service (`package main`) built on `gorilla/mux` and
`mattn/go-sqlite3`. One source file plus one test file.

## Modules / Flow

- **`main.go`** (277 lines)
  - `main()` — initializes the DB, wires 6 routes on a `mux.Router`, serves on `:8080`.
  - `initDB()` / `closeDB()` — opens `./books.db`, creates the `books` table (`id` autoincrement, `title`/`author` NOT NULL, `year`, `isbn`).
  - Handlers: `healthCheck`, `getBooks` (with `?author=` LIKE filter), `getBook`, `createBook`, `updateBook`, `deleteBook`.
  - Global `db *sql.DB` shared across handlers.
- **`main_test.go`** (402 lines) — 8 `httptest`-based tests covering health, create, list, get-by-id, update, delete (incl. 404-after-delete), and author filtering. `TestMain` bootstraps and tears down the DB.

## Interfaces

- Data model: `Book{ID, Title, Author, Year, ISBN}` with JSON tags.
- REST surface: `POST/GET /books`, `GET/PUT/DELETE /books/{id}`, `GET /health`.
- Persistence: SQLite file DB via `database/sql`.

## Notes

- Success responses are JSON; error responses use `http.Error` (text/plain).
- SQL-not-found detected by string-comparing the error message rather than `errors.Is(err, sql.ErrNoRows)`.
