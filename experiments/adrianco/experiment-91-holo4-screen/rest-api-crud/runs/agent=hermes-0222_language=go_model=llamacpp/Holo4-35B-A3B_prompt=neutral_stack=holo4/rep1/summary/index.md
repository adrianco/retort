# Codebase Summary — rest-api-crud (go, Holo4-35B-A3B)

Single-package Go program (`package main`) implementing a book-collection REST API
on the stdlib `net/http` mux with `modernc.org/sqlite` (CGo-free) as the store.

## Modules / files

| File | Role |
|------|------|
| `main.go` (384 L) | Everything: types, DB init, handlers, router, `main()` |
| `main_test.go` (331 L) | 10 `httptest`-based handler tests (incl. a 4-case table) |
| `README.md` | Setup, run, and per-endpoint `curl` examples |
| `go.mod` / `go.sum` | Module + pinned deps (only `modernc.org/sqlite` + transitive) |

## Interfaces

- **Types:** `Book`, `CreateBookRequest`, `UpdateBookRequest` (pointer fields → PATCH-style partial update).
- **Helpers:** `writeJSON`, `writeError` centralize response encoding + Content-Type.
- **DB:** package-global `*sql.DB` opened in `initDB()` (also re-opened per test in `setupTestDB`).

## Request flow

`main()` registers `/health`, `/books`, `/books/` → `booksHandler` dispatches on path
shape (`/books` vs `/books/{id}`) and method, delegating to per-verb handlers. ID is
parsed from the path via `strings.TrimPrefix` + `strconv.ParseInt`. Updates build a
dynamic `UPDATE ... SET` from the non-nil request fields.

## Notable design points

- Handlers are package-level funcs taking `(w, r)`, so tests call them directly without a live listener.
- `:memory:` SQLite — see findings (R7): the engine is SQLite but storage is non-persistent.
- Validation on create is stricter than the spec (year + isbn also required).
