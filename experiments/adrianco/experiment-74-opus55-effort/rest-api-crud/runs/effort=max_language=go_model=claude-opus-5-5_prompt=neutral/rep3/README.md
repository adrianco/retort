# Book Collection API

A REST API for managing a book collection, written in Go. It uses the standard
library's `net/http` router and stores books in SQLite.

## Requirements

- Go 1.25 or newer.

That is all. The SQLite driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite))
is pure Go, so no C compiler or system SQLite library is needed, and the
service builds with `CGO_ENABLED=0`.

## Running

```sh
go run .
```

or build a binary first:

```sh
go build -o bookapi .
./bookapi
```

The server listens on port 8080 and keeps its data in `books.db` in the
current directory, creating the file on first start.

| Flag    | Environment variable | Default    | Description                                                  |
|---------|----------------------|------------|--------------------------------------------------------------|
| `-addr` | `PORT` (port only)   | `:8080`    | Address to listen on                                         |
| `-db`   | `DB_PATH`            | `books.db` | SQLite database file; `:memory:` for a throwaway database    |

Flags take precedence over environment variables, for example
`./bookapi -addr 127.0.0.1:9000 -db /var/lib/books.db` or
`PORT=9000 DB_PATH=/tmp/books.db go run .`.

Stop the server with Ctrl+C or `SIGTERM`. It stops accepting connections and
gives in-flight requests up to 10 seconds to finish. Each request is logged
to stderr with its method, path, status and duration.

## API

### The book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

| Field    | Type             | Rules                                                          |
|----------|------------------|----------------------------------------------------------------|
| `id`     | integer          | Assigned by the server. IDs of deleted books are never reused. |
| `title`  | string           | **Required.** At most 500 characters.                          |
| `author` | string           | **Required.** At most 300 characters.                          |
| `year`   | integer or null  | Optional. Between 1 and next year. `null` when unknown.        |
| `isbn`   | string           | Optional. At most 32 characters. `""` when unknown.            |

The server trims leading and trailing whitespace from text fields, so a
title or author made only of spaces counts as missing. It ignores fields it
does not know, so a client can `PUT` back a book exactly as it received it,
`id` included. The URL, not the body, decides which book is updated.

### Endpoints

| Method   | Path                  | Success                                         | Errors             |
|----------|-----------------------|-------------------------------------------------|--------------------|
| `GET`    | `/health`             | `200` `{"status":"ok"}`                         | `503` database unavailable |
| `POST`   | `/books`              | `201` the new book, plus a `Location` header    | `400`, `413`       |
| `GET`    | `/books`              | `200` array of books, ordered by `id`           |                    |
| `GET`    | `/books?author=Name`  | `200` array of that author's books              |                    |
| `GET`    | `/books/{id}`         | `200` the book                                  | `400`, `404`       |
| `PUT`    | `/books/{id}`         | `200` the updated book                          | `400`, `404`, `413`|
| `DELETE` | `/books/{id}`         | `204` with no body                              | `400`, `404`       |

- **Author filter.** `?author=` matches the whole author name. Case (ASCII
  letters only) and surrounding spaces are ignored, and partial names do not
  match: `?author=frank%20herbert` finds Frank Herbert's books, but
  `?author=Herbert` finds none. An empty value means no filter. A search with
  no results returns `[]`, never `null`.
- **PUT replaces the whole book.** Send every field, as for `POST`. Title and
  author are required, and optional fields left out are cleared.

### Errors

Every error response is JSON with an `error` message. Validation failures
also include a `fields` object that lists every invalid field at once:

```json
{
  "error": "validation failed: author is required; title is required",
  "fields": {
    "author": "is required",
    "title": "is required"
  }
}
```

| Status | When                                                                          |
|--------|-------------------------------------------------------------------------------|
| `400`  | Malformed JSON, wrong field types, failed validation, or an `id` that is not an integer |
| `404`  | No book with that `id`, or no such route                                      |
| `405`  | Method not supported on that path. The `Allow` header lists the ones that are |
| `413`  | Request body larger than 1 MiB                                                |
| `500`  | Unexpected server error. The details are logged, not returned                 |
| `503`  | `/health` only: the database is unreachable                                   |

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all, or filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=frank%20herbert'

# Fetch one
curl localhost:8080/books/1

# Replace
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health check
curl localhost:8080/health
```

## Testing

```sh
go test ./...
go test -race ./...   # the race detector needs cgo, i.e. a C compiler
go test -v -run TestBookLifecycle ./...
```

The tests need no running server or setup. The HTTP tests start the API in
process with `net/http/httptest`. Every test uses a fresh SQLite file in a
temporary directory, so the real database and driver are exercised and
nothing is mocked. The tests cover:

- **Validation rules** (`book_test.go`): required fields, length limits
  counted in characters rather than bytes, and year bounds.
- **Storage** (`store_test.go`): create, read, update and delete, persistence
  across a restart, IDs never reused, and `:memory:` mode.
- **The HTTP API** (`handlers_test.go`):
  - a full create-read-update-delete lifecycle
  - status codes, headers and error bodies
  - the author filter
  - malformed, mistyped and oversized bodies
  - JSON 404s and 405s
  - 50 concurrent creates
  - database failures that return a 500 without leaking internals
  - panic recovery and request logging
- **Graceful shutdown** (`main_test.go`): a request still in flight when
  shutdown starts completes normally.

## Project layout

| File          | Contents                                                        |
|---------------|-----------------------------------------------------------------|
| `main.go`     | Configuration, startup and graceful shutdown                    |
| `server.go`   | Routes, middleware (request logging, panic recovery) and JSON responses |
| `handlers.go` | Endpoint handlers and request decoding                          |
| `book.go`     | The book model, input normalization and validation              |
| `store.go`    | SQLite persistence                                              |
| `*_test.go`   | Tests                                                           |

## Design notes

- **No web framework.** Go's standard `ServeMux` supports method-based routes
  and path parameters, such as `GET /books/{id}`, which is all this API needs.
  The only third-party dependency is the SQLite driver.
- **A single SQLite connection.** SQLite allows only one writer at a time.
  With one pooled connection, concurrent requests queue cheaply inside
  `database/sql` instead of hitting SQLite's sleep-and-retry busy handler.
  In tests, 50 concurrent inserts took about 10 ms this way, against 70 to
  560 ms with a connection per request. The database runs in WAL mode, so
  other processes such as the `sqlite3` shell can still read it while the
  server writes.
- **The schema is created at startup** with `CREATE TABLE IF NOT EXISTS`.
  That is enough for a single table. A real migration tool would be the next
  step if the schema starts to change.
