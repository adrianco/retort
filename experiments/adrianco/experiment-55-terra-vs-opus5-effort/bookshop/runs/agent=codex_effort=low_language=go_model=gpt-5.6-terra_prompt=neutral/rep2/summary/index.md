# Architecture Summary

Single-file Go HTTP service (`main.go`, 231 LOC) plus tests (`main_test.go`, 79 LOC).
No web framework — uses the stdlib `net/http` with a hand-rolled router in `API.ServeHTTP`.

## Modules

- **`Book`** — domain struct (id, title, author, year, isbn) with JSON tags.
- **`API`** — wraps `*sql.DB`. `NewAPI` creates the `books` table (idempotent `CREATE TABLE IF NOT EXISTS`).
- **`ServeHTTP`** — path/method dispatch:
  - `/health` → GET status ok
  - `/books` → POST (create), GET (list, optional `?author=` exact filter)
  - `/books/{id}` → GET / PUT / DELETE, with id parsed via `strconv.ParseInt`
- **Handlers** — `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`; helpers `decodeBook`, `writeJSON`, `writeError`, `methodNotAllowed`.
- **Persistence** — SQLite via `github.com/mattn/go-sqlite3` (CGO). DSN from `BOOKS_DB` env (default `books.db`); listen addr from `ADDR` (default `:8080`).

## Request flow

`ServeHTTP` → path match → method switch → handler → parameterized SQL query → `writeJSON`.
Validation (`title`/`author` required, trimmed) lives in `decodeBook`, which also sets
`DisallowUnknownFields` and a 1 MiB body cap. Correct status codes: 201 create, 200 get/list/update,
204 delete, 400 validation, 404 missing/bad id, 405 method, 500 db errors.
