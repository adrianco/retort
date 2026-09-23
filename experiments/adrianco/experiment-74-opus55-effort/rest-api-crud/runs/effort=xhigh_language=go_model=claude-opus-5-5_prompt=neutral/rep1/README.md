# Book Collection API

A REST API for managing a book collection, written in Go. It uses the standard
library `net/http` router (Go 1.22+ method and path patterns) and stores data in
SQLite through [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a
pure-Go driver. Because it needs no cgo, you don't need a C compiler or a system
SQLite library.

## Requirements

- Go 1.25 or newer (required by the SQLite driver)

## Setup and run

```bash
go mod download          # fetch dependencies
go run .                 # serves on :8080, stores data in ./books.db
```

To build a binary instead:

```bash
go build -o bookapi .
./bookapi -addr :9000 -db /var/lib/bookapi/books.db
```

### Configuration

| Flag    | Environment variable | Default    | Description                                      |
|---------|----------------------|------------|--------------------------------------------------|
| `-addr` | `ADDR` (or `PORT`)   | `:8080`    | Listen address. `PORT=9000` means `:9000`.       |
| `-db`   | `DB_PATH`            | `books.db` | SQLite file (created if missing), or `:memory:`. |

Flags take precedence over environment variables. The server logs each request
to stderr. On `SIGINT` or `SIGTERM` it shuts down gracefully, letting in-flight
requests finish (up to 10 seconds).

## Running the tests

```bash
go test ./...            # all tests
go test -race -v ./...   # verbose, with the race detector
```

Each test gets its own temporary SQLite file, so the tests don't depend on each
other or on any existing `books.db`. There are four test files:

- `book_test.go`: input normalization and validation rules (required fields,
  length limits, year range, ISBN formats).
- `store_test.go`: the SQLite layer. Covers CRUD, the author filter,
  not-found errors, persistence across a close and reopen, deleted IDs not
  being reused, and `:memory:` mode.
- `handlers_test.go`: end-to-end HTTP tests through a real `httptest.Server`.
  Covers every endpoint, status codes, validation and malformed-body errors,
  413 for oversized bodies, JSON 404/405 responses, the health check with the
  database down, panic recovery, and concurrent writes.
- `main_test.go`: resolving the listen address.

## API

Every response body, including errors, is JSON (`Content-Type: application/json`).

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-17271-9",
  "created_at": "2026-09-22T19:43:26.943Z",
  "updated_at": "2026-09-22T19:43:26.943Z"
}
```

`id`, `created_at` and `updated_at` are set by the server. Any values the client
sends for them are ignored.

### Endpoints

| Method   | Path          | Success                          | Errors            |
|----------|---------------|----------------------------------|-------------------|
| `GET`    | `/health`     | `200` `{"status":"ok"}`          | `503`             |
| `POST`   | `/books`      | `201` book + `Location` header   | `400`, `413`      |
| `GET`    | `/books`      | `200` array of books             |                   |
| `GET`    | `/books/{id}` | `200` book                       | `400`, `404`      |
| `PUT`    | `/books/{id}` | `200` updated book               | `400`, `404`, `413` |
| `DELETE` | `/books/{id}` | `204` no body                    | `400`, `404`      |

Other responses:

- An unsupported method on a known path returns `405` with an `Allow` header.
- An unknown path returns `404`.
- An unexpected server error returns `500` with a generic message. The details
  go to the server log only.

### Examples

```bash
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# List all, or filter by author (exact match, case-insensitive)
curl localhost:8080/books
curl 'localhost:8080/books?author=frank%20herbert'

# Get one
curl localhost:8080/books/1

# Replace (PUT sends the full book)
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

### Validation

The server trims leading and trailing whitespace from `title`, `author` and
`isbn`, then checks the following:

| Field    | Rule                                                                      |
|----------|---------------------------------------------------------------------------|
| `title`  | Required, non-blank, at most 500 characters.                              |
| `author` | Required, non-blank, at most 200 characters.                              |
| `year`   | Optional. `0` or omitted means unknown. Otherwise 1 through next year.    |
| `isbn`   | Optional. 10 or 13 digits, and may include hyphens or spaces. An ISBN-10 may end in `X`. |

A validation failure returns `400` and lists every invalid field:

```json
{
  "error": "validation failed",
  "fields": {
    "author": "author is required",
    "title": "title is required"
  }
}
```

A body problem returns a single message, for example
`{"error": "malformed JSON at byte offset 14"}` or
`{"error": "field \"year\" must be of type int"}`. Body problems include an
empty body, malformed JSON, a wrong field type, a non-object body, and trailing
data after the object. A body larger than 1 MiB returns `413`.

## Design notes

- **`PUT` replaces the whole book.** `title` and `author` are required, as they
  are for create. If you omit `year` or `isbn`, they are cleared.
  `created_at` is preserved and `updated_at` is refreshed.
- **The author filter is an exact match that ignores ASCII case.**
  `?author=jane austen` matches "Jane Austen" but not "Jane Austen Society".
  An empty `?author=` returns all books.
- **Duplicate books are allowed.** A collection can hold several copies of the
  same edition, so ISBNs are not unique.
- **ISBNs are checked for shape, not checksum.** The server stores an ISBN
  exactly as submitted, apart from trimming. It checks the format but not the
  check digit, so mistyped or legacy identifiers can still be recorded.
- **IDs are never reused** (`AUTOINCREMENT`). A deleted book's URL keeps
  returning `404` and never points to a different book.
- **SQLite runs in WAL mode with a busy timeout.** Concurrent requests wait for
  the write lock instead of failing with `SQLITE_BUSY`. A test covers this.

## Project layout

```
main.go       entry point: config, server, graceful shutdown
handlers.go   routes, HTTP handlers, JSON helpers, middleware
book.go       Book model, input normalization and validation
store.go      SQLite persistence
*_test.go     tests
```
