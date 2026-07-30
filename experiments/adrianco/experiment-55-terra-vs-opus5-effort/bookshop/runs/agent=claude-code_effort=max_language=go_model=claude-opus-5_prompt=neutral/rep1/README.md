# bookapi

A small REST API for managing a book collection, written in Go and backed by
SQLite.

- **Framework:** none — the Go standard library (`net/http` with the method-aware
  `ServeMux` routing patterns added in Go 1.22).
- **Database:** SQLite via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
  a pure-Go driver. No cgo, no C toolchain, no system SQLite required.

## Requirements

Go 1.25 or newer (the floor comes from the SQLite driver). That is all —
`go build` fetches the one dependency.

## Setup and run

```sh
go mod download          # optional; go build/test will do this too
go build -o bookapi .
./bookapi
```

The server listens on `:8080` and creates `books.db` in the working directory on
first start. Check that it is up:

```sh
curl -s localhost:8080/health
# {"status":"ok","database":"up"}
```

To run without building a binary first:

```sh
go run .
```

### Configuration

Each option can be set with a flag or an environment variable; the flag wins.

| Flag          | Environment variable | Default    | Meaning                                  |
| ------------- | -------------------- | ---------- | ---------------------------------------- |
| `-addr`       | `BOOKAPI_ADDR`       | `:8080`    | Address to listen on (`host:port`)       |
| `-db`         | `BOOKAPI_DB`         | `books.db` | Path to the SQLite file; `:memory:` works |
| `-log-level`  | `BOOKAPI_LOG_LEVEL`  | `info`     | `debug`, `info`, `warn` or `error`       |

```sh
./bookapi -addr 127.0.0.1:9000 -db /var/lib/bookapi/books.db -log-level debug
```

The server shuts down gracefully on `SIGINT` or `SIGTERM`, giving in-flight
requests up to 15 seconds to finish.

## API

All responses are JSON (`application/json; charset=utf-8`), except `204 No
Content`, which has an empty body.

| Method   | Path           | Success | Description                          |
| -------- | -------------- | ------- | ------------------------------------ |
| `GET`    | `/health`      | 200     | Liveness check; also pings the database |
| `POST`   | `/books`       | 201     | Create a book                        |
| `GET`    | `/books`       | 200     | List books, optionally `?author=`    |
| `GET`    | `/books/{id}`  | 200     | Fetch one book                       |
| `PUT`    | `/books/{id}`  | 200     | Replace a book                       |
| `DELETE` | `/books/{id}`  | 204     | Delete a book                        |

### The book object

```json
{
  "id": 1,
  "title": "The Hitchhiker's Guide to the Galaxy",
  "author": "Douglas Adams",
  "year": 1979,
  "isbn": "0345391802",
  "created_at": "2026-07-30T02:43:15.610192Z",
  "updated_at": "2026-07-30T02:43:15.610192Z"
}
```

`year` and `isbn` are optional and are returned as `null` when unset, so a `GET`
response can be fed straight back into a `PUT`. Timestamps are UTC, RFC 3339.

### Validation

| Field    | Rule                                                                        |
| -------- | --------------------------------------------------------------------------- |
| `title`  | **Required.** Trimmed; at most 500 characters                                |
| `author` | **Required.** Trimmed; at most 300 characters                                |
| `year`   | Optional. Between 1 and five years from now                                  |
| `isbn`   | Optional. 10 or 13 digits, `X` allowed as the last character of an ISBN-10   |

Hyphens and spaces are stripped from `isbn` before it is stored, so
`978-0-441-01359-3` and `9780441013593` are the same ISBN. Only the shape is
checked, not the check digit — real catalogues contain ISBNs that fail the
checksum, and rejecting them would lose valid data over someone else's typo.
ISBNs are unique across the collection; any number of books may have none.

A rejected payload lists every problem at once, so a client can fix them in one
round trip:

```json
{
  "error": "validation failed",
  "details": ["title is required", "author is required"]
}
```

### Status codes

| Code | When                                                                |
| ---- | ------------------------------------------------------------------- |
| 200  | `GET` and `PUT` succeeded                                            |
| 201  | Book created; the `Location` header points at the new resource       |
| 204  | Book deleted                                                         |
| 400  | Validation failed, malformed JSON, or a non-numeric/non-positive id  |
| 404  | No book with that id, or no such route                               |
| 405  | Wrong method for the path; the `Allow` header lists the right ones   |
| 409  | Another book already has that ISBN                                   |
| 413  | Request body larger than 1 MiB                                       |
| 415  | `Content-Type` was set to something other than `application/json`    |
| 500  | Unexpected server-side failure (details are logged, not returned)    |
| 503  | The health check could not reach the database                        |

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List everything, then filter by author (case-insensitive)
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=frank%20herbert'

# Fetch one
curl -s localhost:8080/books/1

# Replace it — PUT replaces the whole record, so omitting `year` clears it
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# Delete
curl -i -X DELETE localhost:8080/books/1
```

## Tests

```sh
go test ./...            # ~25 tests, under two seconds
go test -race -cover ./...
```

The suite has three layers:

- `book_test.go` — table-driven unit tests for cleaning and validation.
- `store_test.go` — storage against a real SQLite file in a temp directory:
  CRUD round-trips, the case-insensitive author filter, `PUT` replacement
  semantics, ISBN uniqueness, survival across a reopen, and 24 concurrent
  writers.
- `server_test.go` — HTTP behaviour, including a full create/read/update/delete
  lifecycle over a real `httptest` server, plus every error path: validation,
  bad ids, malformed JSON, wrong content type, oversized bodies, wrong methods,
  unknown routes, panic recovery, and a health check against a downed database.
- `main_test.go` — the actual entry point: flag parsing, startup failures, and
  graceful shutdown on context cancellation.

## Design notes

**Why no framework.** Since Go 1.22 the standard `ServeMux` handles method
matching and path wildcards (`GET /books/{id}`), which is all this API needs.
The only non-stdlib dependency is the SQLite driver.

Two method-less patterns (`/books`, `/books/{id}`) sit behind the real routes.
`ServeMux` prefers the more specific method-bearing pattern, so these only catch
requests that used the wrong verb — which is how a wrong method gets a JSON 405
with an `Allow` header instead of the stdlib's plain-text default.

**Layering.** `book.go` holds the model and its validation rules with no
knowledge of HTTP or SQL; `store.go` owns persistence and returns sentinel
errors (`ErrNotFound`, `ErrDuplicateISBN`); `server.go` translates those into
status codes in one place (`Server.fail`), so handlers stay short and no layer
leaks into another.

**Optional fields are pointers.** `*int` and `*string` distinguish "absent" from
"zero", which is what makes `PUT` a true replacement and lets `year: null` mean
something different from `year: 0`.

**Timestamps** are stored as RFC 3339 text in UTC. It round-trips exactly, sorts
lexicographically, and does not depend on the driver's date handling.

**Concurrency.** The database runs in WAL mode with a 5-second busy timeout, so
readers do not block the writer and concurrent writers queue instead of failing.
An in-memory database is pinned to a single connection, because every new
connection to `:memory:` would otherwise get its own empty database.

**Robustness.** Request bodies are capped at 1 MiB, bodies with trailing content
after the first JSON object are rejected rather than silently truncated,
responses are marshalled before any status code is written so an encoding
failure cannot produce a half-written 200, and a panic in a handler becomes a
500 instead of taking the process down.
