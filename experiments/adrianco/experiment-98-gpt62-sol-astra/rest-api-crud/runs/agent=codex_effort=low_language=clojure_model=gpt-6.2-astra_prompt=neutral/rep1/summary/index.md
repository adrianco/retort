# Architecture Summary — books (Clojure REST API)

Single-namespace Ring/Jetty service backed by SQLite via `clojure.java.jdbc`.
144 LOC across two files (`books.clj` 80, `books_test.clj` 64).

## Modules

- **`books`** (`books.clj`) — the whole service.
  - `open-db` — opens a JDBC SQLite connection and creates the `books` table
    (`id` autoincrement PK, `title`/`author` NOT NULL, `year`, `isbn`).
  - `response` / `missing` / `method-error` / `invalid` — JSON response helpers;
    `invalid` throws `ex-info` with a `:status 400` carried in ex-data.
  - `book-values` — parses + validates the request body (strict JSON, nonblank
    `title`/`author`, optional integer `year`, optional string `isbn`).
  - `collection-route` — `/books`: GET (all, or `?author=` filtered) and POST
    (INSERT ... RETURNING *, 201 + `Location`).
  - `item-route` — `/books/{id}`: GET / PUT (UPDATE ... RETURNING *) / DELETE.
  - `handler` — router over `uri`; dispatches `/health`, `/books`, and the
    `/books/{id}` regex; one try/catch maps `ex-info` → its status and anything
    else → 500.
  - `-main` — boots Jetty on `PORT` (default 8080), DB at `BOOKS_DB`.

- **`books-test`** (`books_test.clj`) — 4 `deftest`s over the ring handler with a
  temp-file SQLite DB fixture: `lifecycle` (CRUD round-trip + 404s after delete),
  `listing` (count + author filter), `validation` (7 bad bodies → 400), and
  `health-and-routing` (/health, 405, 404).

## Flow

HTTP request → `handler` → URI dispatch → `collection-route`/`item-route` →
`jdbc/query`/`execute!` against SQLite → `response` serializes JSON. Validation
errors surface via thrown `ex-info` caught centrally and rendered as 400.

## Notes

- Persistence is real SQLite (`org.xerial/sqlite-jdbc`), file-based, with
  `RETURNING *` used to echo created/updated rows in one round-trip.
- No framework beyond Ring/Jetty + jdbc; routing is hand-rolled, which keeps the
  surface small and idiomatic for the task size.
