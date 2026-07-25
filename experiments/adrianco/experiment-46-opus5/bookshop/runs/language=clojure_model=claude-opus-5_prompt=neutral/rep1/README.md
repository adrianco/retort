# Book API

A small REST service for managing a book collection, written in Clojure.

- **HTTP** — Ring + Jetty, routed with Compojure
- **Storage** — SQLite via `next.jdbc` and the `org.xerial/sqlite-jdbc` driver
- **JSON** — Cheshire, wired up with a thin middleware in `book-api.middleware`

## Setup

You need two things installed:

- A JDK, 17 or newer
- The [Clojure CLI](https://clojure.org/guides/install_clojure) (`clj` / `clojure`)

```bash
# macOS
brew install openjdk@21 clojure/tools/clojure
```

No database server is needed — SQLite writes to a local file, created on first
start. Dependencies are fetched by the Clojure CLI on the first run.

### Finding the JDK

The Clojure CLI locates a JVM through `$JAVA_HOME` or `$PATH` only, so an
otherwise fine installation can still fail with *"Unable to locate a Java
Runtime"* — Homebrew's `openjdk` formulae are keg-only and never land on
`PATH`, and macOS ships a `/usr/bin/java` stub that only prints that error.

The `./run.sh` and `./test.sh` wrappers below handle this: they source
`bin/java-env.sh`, which probes the usual locations (`/usr/libexec/java_home`,
Homebrew, SDKMAN, `/usr/lib/jvm`) and exports `JAVA_HOME` before invoking
`clojure`. Use them if the bare `clj` commands do not work; otherwise the two
are interchangeable. To skip the wrappers entirely, export `JAVA_HOME` yourself:

```bash
export JAVA_HOME=$(/usr/libexec/java_home)     # or /opt/homebrew/opt/openjdk@21
```

## Run

```bash
./run.sh          # or: clj -M:run
```

The service listens on <http://localhost:3000> and stores data in `./books.db`.
Both are configurable through the environment:

```bash
PORT=8080 BOOK_API_DB=/tmp/library.db ./run.sh
```

## Test

```bash
./test.sh         # or: make test, clj -M:test, clj -X:test
```

This runs the full suite: validation unit tests, persistence-layer tests against
a temporary SQLite file, and integration tests that drive the assembled Ring
handler end to end. The command exits non-zero if anything fails.

```
Ran 21 tests containing 119 assertions.
0 failures, 0 errors.
```

## API

All responses are `application/json; charset=utf-8`.

### `GET /health`

Confirms the process is up and that the database answers a query.

```bash
curl localhost:3000/health
# 200 {"status":"ok","database":"up"}
```

Returns `503` with `{"status":"degraded","database":"down"}` if the database is
unreachable.

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are
optional. Returns `201` with the stored book and a `Location` header.

```bash
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```
HTTP/1.1 201 Created
Location: /books/1

{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}
```

### `GET /books`

Lists all books, oldest id first. Pass `?author=` to filter by author — the
match is exact but case-insensitive.

```bash
curl 'localhost:3000/books'
curl 'localhost:3000/books?author=frank%20herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if there is no such id.

### `PUT /books/{id}`

Replaces a book. The body is validated exactly like `POST`, so `title` and
`author` must be present; omitting `year` or `isbn` clears them.

```bash
curl -X PUT localhost:3000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe Edition)","author":"Frank Herbert","year":2019}'
```

### `DELETE /books/{id}`

Deletes a book. Returns `204` with an empty body, or `404` if it was already
gone.

## Status codes

| Code  | When |
|-------|------|
| `200` | Successful read or update |
| `201` | Book created |
| `204` | Book deleted |
| `400` | Validation failed, or the request body was not valid JSON |
| `404` | No book with that id, or an unrecognised route |
| `409` | The `isbn` is already used by a different book |
| `500` | Unexpected server error |
| `503` | Health check could not reach the database |

## Validation

`title` and `author` must be non-blank strings of at most 500 characters;
surrounding whitespace is trimmed before storing. `year`, when supplied, must be
an integer between 1 and 2200 (a numeric string such as `"1965"` is accepted and
coerced). `isbn`, when supplied, must be a non-blank string of at most 32
characters, and is unique across the collection.

Failures come back as a `400` listing every problem at once, rather than only
the first:

```bash
curl -X POST localhost:3000/books \
  -H 'Content-Type: application/json' -d '{"year":1999}'
```

```json
{
  "error": "Validation failed",
  "details": [
    {"field": "title",  "message": "is required"},
    {"field": "author", "message": "is required"}
  ]
}
```

## Layout

```
deps.edn                        dependencies and the :run / :test aliases
Makefile                        make run / make test / make repl / make clean
run.sh, test.sh                 wrappers that locate a JDK, then call clojure
bin/java-env.sh                 JDK discovery, sourced by the wrappers
src/book_api/core.clj           entry point — migrate, then start Jetty
src/book_api/handler.clj        routes, handlers, middleware stack
src/book_api/db.clj             SQLite queries
src/book_api/validation.clj     payload validation and coercion
src/book_api/middleware.clj     JSON encode/decode, error handling
test/book_api/validation_test.clj
test/book_api/db_test.clj
test/book_api/api_test.clj      end-to-end tests through the Ring handler
test/book_api/test_support.clj  temporary-database fixture and helpers
test/book_api/test_runner.clj   `clj -M:test` entry point
```
