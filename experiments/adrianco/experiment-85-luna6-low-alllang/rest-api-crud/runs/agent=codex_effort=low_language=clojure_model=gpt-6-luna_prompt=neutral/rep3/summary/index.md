# Architecture Summary — book-api (Clojure)

A small Compojure/Ring REST service backed by embedded SQLite via raw JDBC.

## Modules

- **`book-api.core`** (`src/book_api/core.clj`, 48 LOC) — HTTP layer. `defroutes app-routes`
  wires the six endpoints plus `/health` and a not-found fallback. `valid-book?` performs
  input validation. `app` composes the handler with `wrap-json-response` and
  `wrap-json-body {:keywords? true}`. `-main` starts Jetty on `PORT` (default 3000).
- **`book-api.db`** (`src/book_api/db.clj`, 73 LOC) — persistence. Lazily opens a single
  shared `java.sql.Connection` (double-checked locking on an atom), creates the `books`
  table, and exposes `all-books`, `find-book`, `create-book`, `update-book`, `delete-book`
  using `PreparedStatement`s. `reset-db!` drops the table (used by tests).
- **`book-api.core-test`** (`test/book_api/core_test.clj`, 30 LOC) — 3 `deftest`s driving
  `api/app` directly with synthetic ring request maps; `use-fixtures` resets the DB.

## Request flow

HTTP → `wrap-json-body` (parses JSON body to keywordized map) → `app-routes` (Compojure
dispatch) → handler validates/queries `book-api.db` → map response → `wrap-json-response`
serializes to JSON.

## Notable

- All SQL uses parameterized `PreparedStatement`s — no injection surface.
- Persistence is real SQLite (`org.xerial/sqlite-jdbc`), file configurable via `BOOKS_DB`.
- **Gap:** no `ring.middleware.params/wrap-params` in the handler stack, so query-string
  parameters (the `?author=` filter) are never parsed into `:params` on a live server.
  See `../findings.jsonl` (R3).
