# Architecture Summary

A small Ring/Compojure REST service over a SQLite file, cleanly split into three
namespaces with a persistence/handler/entrypoint separation.

## Modules

| Namespace | File | Responsibility |
|-----------|------|----------------|
| `books.db` | `src/books/db.clj` | Persistence via next.jdbc + SQLite. `datasource`, `init!` (schema), and CRUD (`get-book`, `list-books`, `create-book!`, `update-book!`, `delete-book!`). Uses `RETURNING` to echo the affected row and `COLLATE NOCASE` for the author filter. |
| `books.handler` | `src/books/handler.clj` | HTTP layer. Builds the Compojure route table, JSON encoding (`json-response`/`error`), body parsing (`parse-body`), validation (`validate`, `with-valid-book`), id parsing, and two middlewares (`wrap-query-params`, `wrap-errors`). `app` composes them. |
| `books.core` | `src/books/core.clj` | Entrypoint. Reads `PORT`/`DB_PATH` env, initialises the datasource, and starts Jetty. |

## Request flow

`-main` → `db/init!` (opens SQLite, creates table) → `handler/app ds` → Jetty.
Each request: `wrap-errors` (500 guard) → `wrap-query-params` (query string only,
deliberately not form body) → route dispatch → `db/*` call → `json-response`.

## Design notes

- Validation requires non-blank string `title`/`author`; `year` must be integer if
  present, `isbn` a string if present. Invalid input → 400 with per-field `details`.
- Non-JSON / non-object bodies → 400; unknown routes and absent ids → 404.
- PUT is full-replace semantics (documented in README).
- Errors are caught centrally and returned as `{"error":..., "details":...}`.

## Tests

`test/books/handler_test.clj` — 8 `deftest`s exercising the handler against a fresh
temp SQLite file per test (`use-fixtures :each`), via `ring.mock`.
