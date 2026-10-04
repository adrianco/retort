# Architecture Summary — books (Clojure REST API)

A small, cleanly layered Ring/Compojure service over an embedded SQLite DB.

## Modules

| Namespace | File | Responsibility |
|-----------|------|----------------|
| `books.core` | `src/books/core.clj` (99 LOC) | HTTP layer: route table, JSON responses, request-body parsing, validation, error/query-param middleware, `-main` entry point. |
| `books.db` | `src/books/db.clj` (53 LOC) | Persistence layer: SQLite datasource, schema init, CRUD via `next.jdbc` with `RETURNING *`. |
| `books.core-test` | `test/books/core_test.clj` (103 LOC) | Integration tests: exercise the full Ring handler against a per-test temp SQLite file. |

## Interfaces / flow

- `-main` → reads `PORT`/`DB_PATH` env → `db/datasource` + `db/init!` → `make-app` → `jetty/run-jetty`.
- `make-app` = `app-routes` wrapped by `wrap-query-params` (parses `?author=`) then `wrap-errors` (catches unhandled exceptions → 500).
- Routes call into `books.db` functions; the DB layer returns unqualified lower-case maps (`rs/as-unqualified-lower-maps`) that serialize directly to JSON via cheshire.
- Validation is centralized in `validate-book` / `with-valid-book`: title+author required non-empty strings; year integer-or-nil; isbn string-or-nil. Invalid or non-object JSON bodies → 400.

## Notable design choices

- `RETURNING *` on INSERT/UPDATE avoids a second round-trip and returns the persisted row (including generated `id`) directly.
- `PUT` is a full replace (omitted optional fields become null) — documented in the README.
- Custom `wrap-query-params` used instead of full `wrap-params` so JSON bodies are never consumed as form data.
