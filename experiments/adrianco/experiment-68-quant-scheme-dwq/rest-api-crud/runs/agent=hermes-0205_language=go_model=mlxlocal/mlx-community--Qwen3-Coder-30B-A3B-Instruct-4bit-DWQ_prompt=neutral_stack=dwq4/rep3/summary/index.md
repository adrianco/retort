# Architecture Summary

Single-package Go service (`package main`) — one source file plus one test file.

## Modules / files

| File | Role |
|------|------|
| `main.go` (326 LOC) | Entire service: data model, DB init, HTTP handlers, router, `main()` |
| `main_test.go` (396 LOC) | 12 `Test*` functions exercising handlers + shared helpers |

## Data model

- `Book{ID, Title, Author, Year, ISBN}` with JSON tags.
- Persistence: SQLite via `github.com/mattn/go-sqlite3`, file `./books.db`, table
  `books` created on start with `title`/`author` `NOT NULL`.

## Interfaces (HTTP routes)

- `GET /health` → `healthHandler` → `{"status":"healthy"}`
- `GET /books` (+ `?author=`) → `getBooksHandler` (author uses `LIKE %…%`)
- `POST /books` → `createBookHandler` (validates title+author, 201 on success)
- `GET /books/{id}` → `getBookHandler` (404 if absent)
- `PUT /books/{id}` → `updateBookHandler` (404 if absent, validates fields)
- `DELETE /books/{id}` → `deleteBookHandler` (404 if absent, 204 on success)

## Routing / flow

`main()` registers three patterns on `DefaultServeMux`: `/health`, `/books`
(exact — list/create), and `/books/` (subtree — dispatches `/books/{id}` by method
and also handles the trailing-slash list/create case). This subtree handler is the
fix for the previous attempt's defect, where `/books/{id}` was never routed.

## Notes

- Tests invoke handler functions **directly** (not through the mux), so the router
  wiring itself is not exercised by any test.
