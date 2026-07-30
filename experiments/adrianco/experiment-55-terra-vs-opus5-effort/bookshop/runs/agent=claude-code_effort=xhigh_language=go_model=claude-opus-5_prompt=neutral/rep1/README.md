# bookapi

A small REST API for managing a book collection, written in Go and backed by an
embedded SQLite database.

- **Language:** Go 1.25+ (developed against 1.26)
- **HTTP:** the standard library `net/http`, using the Go 1.22 `ServeMux`
  pattern router — no web framework
- **Storage:** SQLite via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
  a pure-Go driver, so the service builds and tests with `CGO_ENABLED=0` and
  needs no system SQLite

## Quick start

```bash
go mod download        # fetch the one dependency
go test ./...          # run the test suite
go run .               # serve on :8080, storing data in ./books.db
```

Then, in another terminal:

```bash
curl localhost:8080/health

curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0-13-419044-0"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Alan+Donovan'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2016}'

curl -X DELETE localhost:8080/books/1
```

> The `Content-Type: application/json` header is required on `POST` and `PUT`.
> `curl -d` defaults to `application/x-www-form-urlencoded`, which the API
> rejects with `415`.

To build a binary instead:

```bash
go build -o bookapi .
./bookapi -addr :9000 -db /var/lib/bookapi/books.db
```

## Configuration

Each flag falls back to an environment variable, then to a default. The command
line wins over the environment.

| Flag          | Environment        | Default    | Meaning                              |
| ------------- | ------------------ | ---------- | ------------------------------------ |
| `-addr`       | `BOOKAPI_ADDR`     | `:8080`    | `host:port` to listen on             |
| `-db`         | `BOOKAPI_DB`       | `books.db` | Path to the SQLite file (created if absent) |
| `-log-level`  | `BOOKAPI_LOG_LEVEL`| `info`     | `debug`, `info`, `warn` or `error`   |

The database file and its schema are created on first start. Logs are JSON on
stderr (`log/slog`). `SIGINT`/`SIGTERM` triggers a graceful shutdown that gives
in-flight requests up to 10 seconds to finish.

## API

All responses are JSON except `204 No Content`.

### `GET /health`

Liveness plus a database round-trip, so a `200` means the service can actually
serve requests.

```json
{ "status": "ok", "database": "ok" }
```

Returns `503` with `"status": "degraded"` if the database is unreachable.

### `POST /books`

Creates a book. Responds `201` with the created record and a `Location` header
pointing at it.

```jsonc
// request
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-441-01359-3" }
```

```jsonc
// 201 Created — Location: /books/1
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "created_at": "2026-07-29T18:42:03.117Z",
  "updated_at": "2026-07-29T18:42:03.117Z"
}
```

### `GET /books`

Lists every book, oldest first. `?author=` filters by author.

```jsonc
{ "books": [ /* … */ ], "count": 2 }
```

The list is wrapped in an object rather than returned as a bare array, so
pagination metadata can be added later without breaking clients. `books` is
always an array, never `null`.

The author filter is an **exact match, case-insensitive** and insensitive to
surrounding whitespace: `?author=alan+donovan` matches `Alan Donovan`, but
`?author=Donovan` matches nothing. An empty `?author=` is treated as no filter.
Any other query parameter is rejected with `400`, so a typo like `?auther=`
fails loudly instead of quietly returning the whole collection.

### `GET /books/{id}`

Returns one book, or `404`.

### `PUT /books/{id}`

Replaces a book. This is a full replacement, not a merge: the body is validated
exactly like a create, and **omitting `year` or `isbn` clears them**. Returns
the stored record with a refreshed `updated_at`; `id` and `created_at` are
preserved.

### `DELETE /books/{id}`

Deletes a book. Responds `204` with an empty body, or `404` if it is already
gone.

## Validation

| Field    | Rule                                                                      |
| -------- | ------------------------------------------------------------------------- |
| `title`  | **Required.** Trimmed of surrounding whitespace; must be non-empty after trimming; at most 512 characters |
| `author` | **Required.** Same handling; at most 256 characters                        |
| `year`   | Optional. `0` (or omitted) means unknown; otherwise between 1 and next year |
| `isbn`   | Optional. Must be a valid ISBN-10 or ISBN-13 including the check digit; unique across the collection |

Limits count characters, not bytes, so a title in CJK or accented text gets the
full budget.

ISBNs are canonicalised before storage — separators are stripped and an ISBN-10
check digit of `x` is upper-cased — so `0-306-40615-2` and `0306406152` are
recognised as the same book. Any number of books may have no ISBN.

## Status codes

| Code  | When                                                                     |
| ----- | ------------------------------------------------------------------------ |
| `200` | Successful `GET` or `PUT`                                                |
| `201` | Book created                                                             |
| `204` | Book deleted                                                             |
| `400` | Malformed JSON, unknown JSON field, non-numeric `{id}`, unknown query parameter |
| `404` | No such book, or no such route                                           |
| `405` | Wrong method for a known route — the response carries an `Allow` header  |
| `409` | The supplied ISBN already belongs to another book                        |
| `413` | Request body over 64 KiB                                                 |
| `415` | Missing or non-JSON `Content-Type` on `POST`/`PUT`                       |
| `422` | Body parsed fine but a field failed validation                           |
| `500` | Unexpected server-side failure (details are logged, not returned)        |
| `503` | `/health` could not reach the database                                   |

`400` and `422` are deliberately distinct: `400` means "I could not understand
this request", `422` means "I understood it and the values are wrong".

### Error format

Every failure returns the same shape. `details` is present for validation
failures and maps each rejected field to its reason:

```jsonc
// 422 Unprocessable Entity
{
  "error": "validation failed",
  "details": {
    "title": "title is required",
    "isbn": "isbn must be a valid ISBN-10 or ISBN-13"
  }
}
```

```jsonc
// 409 Conflict
{ "error": "isbn already belongs to another book" }
```

## Project layout

```
main.go                     flag parsing, wiring, listener, graceful shutdown
internal/books/book.go      the Book model and its validation rules
internal/books/isbn.go      ISBN-10/13 canonicalisation and check digits
internal/books/store.go     SQLite schema, queries and error translation
internal/api/server.go      routing and Server construction
internal/api/handlers.go    one handler per endpoint
internal/api/decode.go      strict JSON request decoding
internal/api/respond.go     JSON responses and error-to-status mapping
internal/api/middleware.go  access logging and panic recovery
```

The `books` package knows nothing about HTTP and the `api` package knows nothing
about SQL; the two meet at `books.Input`, `books.Book` and the sentinel errors
`books.ErrNotFound` and `books.ErrDuplicateISBN`, which `respondError` maps onto
`404` and `409`.

## Tests

```bash
go test ./...              # ~1s
go test -race ./...        # the suite is race-clean
go test -cover ./...       # ~86% of statements
```

40 tests, most of them table-driven, covering:

- **`internal/books`** — ISBN check digits and canonical forms; every validation
  rule; store CRUD; `ErrNotFound` from get/update/delete; the ISBN uniqueness
  constraint and the partial index that still allows many books without one;
  the author filter's case handling; **persistence across a close and reopen**;
  and concurrent writers.
- **`internal/api`** — a full create/read/list/update/delete lifecycle; the
  `Location` header; `PUT` replace semantics; validation surfaced as `422` with
  per-field details; malformed bodies, wrong content types and oversized bodies;
  routing errors including `Allow` headers on `405`; health reporting `503` when
  the database is closed; `HEAD` reporting the same `Content-Length` as `GET`;
  concurrent requests; and one pass over a real `httptest` listener rather than
  a recorder.
- **`main`** — the binary binds a port, serves `/health`, and shuts down cleanly
  when its context is cancelled; bad configuration is rejected.

Tests use a fresh SQLite file per test in `t.TempDir()`, so they are isolated
and run in parallel.

## Design notes

**Why a pure-Go SQLite driver.** `modernc.org/sqlite` avoids cgo, which keeps
the build simple, cross-compilable and free of a C toolchain requirement. The
better-known `mattn/go-sqlite3` would work but needs cgo.

**Connection pool of one.** SQLite allows a single writer at a time. Rather than
scatter retry logic around `SQLITE_BUSY`, the pool is capped at one connection
(`store.go`), which serialises access. At this scale it costs nothing and
removes a class of intermittent failure; the concurrency tests exercise it. WAL
journalling and a 5-second busy timeout are set as connection pragmas.

**Strict decoding.** Unknown JSON fields, trailing content after the object and
non-JSON content types are all errors. A misspelled `"titel"` should not
silently create a book with no title.

**The `{id}` distinction.** `/books/abc` is `400`, not `404` — no book could
ever have that ID, so the request itself is malformed. `/books/999` is `404`.
