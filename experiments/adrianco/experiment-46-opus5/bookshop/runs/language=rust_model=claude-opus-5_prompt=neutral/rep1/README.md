# book-api

A small REST service for managing a book collection, written in Rust with
[axum](https://docs.rs/axum) and [SQLite](https://docs.rs/rusqlite) (bundled —
no system SQLite install needed).

## Requirements

- Rust 1.85+ (edition 2024). Tested with 1.96.
- A C compiler, which `libsqlite3-sys` uses to build the bundled SQLite. macOS:
  Xcode command line tools. Debian/Ubuntu: `build-essential`.

No other services or setup steps: the database file is created on first start.

## Run

```bash
cargo run                       # http://127.0.0.1:3000, data in ./books.db
```

Configuration is read from the environment:

| Variable    | Default          | Meaning                                            |
| ----------- | ---------------- | -------------------------------------------------- |
| `BOOKS_DB`  | `books.db`       | SQLite file path. `:memory:` for a throwaway store. |
| `BIND_ADDR` | `127.0.0.1:3000` | Address to listen on.                              |

```bash
BOOKS_DB=:memory: BIND_ADDR=0.0.0.0:8080 cargo run --release
```

## Test

```bash
cargo test
```

That runs the validation unit tests (`src/models.rs`) plus 13 integration tests
(`tests/api.rs`) which exercise the real router end to end against a private
in-memory database — every route, both success and failure paths.

## API

All responses are JSON, except `204 No Content` which has an empty body.

### `GET /health`

Confirms the process is up **and** that the database answers a query.

```json
{ "status": "ok", "books": 2 }
```

### `POST /books`

`title` and `author` are required and must be non-blank; `year` and `isbn` may
be omitted or `null`. Leading/trailing whitespace is trimmed. Returns `201` with
a `Location` header pointing at the new resource.

```bash
curl -X POST localhost:3000/books \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-01359-3"
}
```

### `GET /books`

Lists books, newest first. `?author=` filters on an exact but **case-insensitive**
match, so `?author=frank+herbert` finds "Frank Herbert". An unmatched filter is
an empty array, not a 404.

```bash
curl 'localhost:3000/books?author=frank+herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if the id is unknown.

### `PUT /books/{id}`

A **full replacement**: the body is validated exactly like `POST`, and fields
you leave out are set to `null`. Returns the updated book, or `404` if the id is
unknown.

```bash
curl -X PUT localhost:3000/books/1 \
  -H 'content-type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
```

### `DELETE /books/{id}`

`204` on success, `404` if the id is unknown (so a repeated delete is not a
silent success).

## Status codes

| Code | When                                                            |
| ---- | --------------------------------------------------------------- |
| 200  | Successful `GET` / `PUT`                                          |
| 201  | Book created                                                      |
| 204  | Book deleted                                                      |
| 400  | Body is not readable JSON, or the path id is not an integer       |
| 404  | No book with that id, or no such route                            |
| 422  | Body parsed but failed validation                                 |
| 500  | Unexpected database failure (detail is logged, not returned)      |

Errors share one shape. Validation errors report **every** problem at once
rather than stopping at the first:

```json
{
  "error": "validation failed",
  "details": ["title is required", "author must not be empty"]
}
```

```json
{ "error": "book 42 not found" }
```

## Validation rules

- `title`, `author` — required, trimmed, non-empty, at most 512 characters.
- `year` — optional; if present must be between -4000 and 2200.
- `isbn` — optional; if present must be 10 or 13 characters once hyphens and
  spaces are stripped (a trailing `X` check digit is allowed on ISBN-10). The
  shape is checked, not the check digit.

## Layout

```
src/
  main.rs      binary: reads env config, binds the socket, serves
  lib.rs       builds the axum Router
  state.rs     shared SQLite connection; runs queries off the async threads
  handlers.rs  one function per route + a JSON extractor with JSON errors
  db.rs        schema and the five SQL statements
  models.rs    Book / BookPayload and validation (+ unit tests)
  error.rs     ApiError -> status code + JSON body
tests/
  api.rs       integration tests over the real router
```

### Design notes

- **One connection behind a mutex.** SQLite serializes writes anyway, and every
  query runs inside `spawn_blocking`, so the async runtime is never stalled.
  A pool (e.g. `r2d2_sqlite`) is the next step if read concurrency ever matters.
- **Validation is a type transition.** `BookPayload::validate` consumes the raw
  body and produces a `ValidBook`; the `db` layer only accepts the latter, so an
  unvalidated payload cannot reach a SQL statement.
- **Every error path returns JSON.** Axum's default rejections for bad bodies
  and bad path segments are plain text, so `ApiJson` and a string-typed path
  parameter re-wrap them in the standard error shape.
