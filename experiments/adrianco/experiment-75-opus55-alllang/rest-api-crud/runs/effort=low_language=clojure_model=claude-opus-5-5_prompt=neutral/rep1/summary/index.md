# Run Summary: books REST API (Clojure)

**Surface:** A small REST service for managing a book collection (CRUD over `/books`
plus a `/health` endpoint), persisted to SQLite. Built on Ring + Compojure +
next.jdbc, with JSON via Cheshire.

- [Modules](modules.md)
- [Interfaces](interfaces.md)

## Control flow

`-main` reads `PORT`/`DB_PATH` from the env, calls `db/make-ds` (which creates the
`books` table if absent) and starts Jetty on `(app ds)`. `app` builds a
`wrap-params`-wrapped Compojure route table; each route handler validates/parses
input via the `with-book-input` / `with-id` combinators, calls a `books.db`
function, and returns a JSON response through `json-resp`. Persistence is delegated
entirely to `books.db`, which uses `next.jdbc.sql` helpers.
