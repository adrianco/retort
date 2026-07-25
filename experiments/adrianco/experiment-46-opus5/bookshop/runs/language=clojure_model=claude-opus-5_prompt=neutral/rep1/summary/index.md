# Architecture Summary — book-api (Clojure)

> Written inline; the `run-summary` skill was not registered in this session.

A small Ring/Jetty REST service, cleanly layered into single-responsibility namespaces.

## Modules (`src/book_api/`)

| Namespace | Responsibility |
|-----------|----------------|
| `core.clj` | Entry point. Builds the SQLite datasource, runs the migration, starts Jetty. Reads `PORT` / `BOOK_API_DB` from the environment. |
| `db.clj` | SQLite persistence via `next.jdbc`. `datasource`, `migrate!` (idempotent DDL), CRUD (`insert-book!`, `find-book`, `list-books`, `update-book!`, `delete-book!`), plus `ping` (health) and `isbn-owner` (uniqueness). Every fn takes `ds` explicitly so tests inject a throwaway DB. |
| `validation.clj` | Pure payload validation/coercion. `validate-book` returns `{:book ..}` or `{:errors [..]}`; `parse-id` coerces path ids to positive longs. Title/author required; year/isbn optional with bounds. |
| `middleware.clj` | Ring middleware: `wrap-json-body` (decode + 400 on malformed), `wrap-json-response` (encode non-string bodies), `wrap-errors` (catch-all → 500 JSON). |
| `handler.clj` | Compojure routes + handlers. Wires middleware in `app`. Maps outcomes to status codes: 201/200/204/400/404/409. |

## Request flow

`Jetty → wrap-errors → wrap-json-response → wrap-json-body → wrap-params → routes → handler → db`

Handlers stay thin: validate → consult db → shape response. Business rules (isbn conflict, id parsing, required fields) live in `validation`/`db`, not in the routing layer.

## Tests (`test/book_api/`)

- `validation_test.clj` (4) — pure unit tests for coercion/validation edge cases.
- `db_test.clj` (9) — persistence layer against a temp SQLite file.
- `api_test.clj` (11) — end-to-end through the Ring handler (ring-mock), including malformed JSON, isbn conflicts, and forced-500 error handling.
- `test_support.clj` — per-test throwaway file DB fixture + request helpers.
- `test_runner.clj` — dependency-free `clj -M:test` / `-X:test` entry point.

24 `deftest` forms total; 0 skipped/disabled.

## Notable design choices

- Datasource threaded as an argument everywhere → trivially testable, no global state.
- Real temp-file SQLite in tests (not `:memory:`) because next.jdbc opens a fresh connection per op.
- ISBN uniqueness enforced at both the DB (`UNIQUE`) and handler (409) levels.
- Case-insensitive author filter via `COLLATE NOCASE`.
