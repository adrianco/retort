# Book Collection API

A small REST API for managing a book collection, written in Go with the standard
library's `net/http` router and backed by SQLite.

## Requirements

- Go 1.26 or newer (`go.mod` pins 1.26.6; older toolchains will download it
  automatically unless `GOTOOLCHAIN=local` is set)

The SQLite driver is [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go implementation, so no C compiler or system SQLite library is needed.

## Setup and run

```bash
go mod download      # fetch dependencies
go run .             # start the server on :8080, storing data in ./books.db
```

Or build a binary:

```bash
go build -o bookapi .
./bookapi
```

Configuration is through environment variables:

| Variable  | Default    | Description                                             |
|-----------|------------|---------------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                                   |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for a non-persistent DB) |

```bash
PORT=9000 DB_PATH=/var/lib/bookapi/books.db ./bookapi
```

The database file and schema are created on first start. The server shuts down
gracefully on `SIGINT`/`SIGTERM`.

## Tests

```bash
go test ./...
```

The tests drive the real HTTP handler against a temporary SQLite database, so
they cover routing, validation and persistence together.

## API

All request and response bodies are JSON.

| Method   | Path          | Description                          | Success          |
|----------|---------------|--------------------------------------|------------------|
| `GET`    | `/health`     | Health check (pings the database)    | `200 OK`         |
| `POST`   | `/books`      | Create a book                        | `201 Created`    |
| `GET`    | `/books`      | List books, optionally `?author=`    | `200 OK`         |
| `GET`    | `/books/{id}` | Get one book                         | `200 OK`         |
| `PUT`    | `/books/{id}` | Replace a book                       | `200 OK`         |
| `DELETE` | `/books/{id}` | Delete a book                        | `204 No Content` |

### Book

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

| Field    | Type    | Rules                                                     |
|----------|---------|-----------------------------------------------------------|
| `id`     | integer | Assigned by the server; ignored in request bodies         |
| `title`  | string  | **Required**, non-blank, at most 500 characters           |
| `author` | string  | **Required**, non-blank, at most 500 characters           |
| `year`   | integer | Optional, 0–9999; `0` when omitted                        |
| `isbn`   | string  | Optional, at most 32 characters; `""` when omitted        |

Leading and trailing whitespace is trimmed from string fields. The ISBN format
is not validated beyond its length.

### Behaviour notes

- `GET /books?author=Frank Herbert` returns only books whose author matches
  exactly, ignoring case. An empty or absent `author` returns every book. The
  result is always a JSON array, ordered by `id`.
- `PUT` is a full replacement: `title` and `author` are required, and an omitted
  `year` or `isbn` is reset to its default.
- `POST` responds with a `Location` header pointing at the new book.

### Errors

Errors are returned as JSON with an `error` message. Validation failures also
include a per-field breakdown:

```json
{
  "error": "validation failed",
  "fields": { "title": "title is required" }
}
```

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Malformed JSON, wrong field type, failed validation, or a non-positive-integer `id` |
| `404`  | No book with that `id`, or an unknown path                           |
| `405`  | Method not supported on that path (see the `Allow` header)           |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected server/database error                                     |
| `503`  | `/health` only: the database is unreachable                          |

### Examples

```bash
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, optionally filtered by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

| File               | Contents                                              |
|--------------------|-------------------------------------------------------|
| `main.go`          | Configuration, server start-up and graceful shutdown  |
| `handlers.go`      | Routing, request decoding, validation, JSON responses |
| `store.go`         | SQLite schema and queries                             |
| `handlers_test.go` | Integration tests through the HTTP handler            |
