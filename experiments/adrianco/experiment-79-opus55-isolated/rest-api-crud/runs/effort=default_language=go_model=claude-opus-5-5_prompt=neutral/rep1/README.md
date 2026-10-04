# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library `net/http` router and SQLite for storage.

SQLite is provided by [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no C compiler or cgo is needed.

## Requirements

- Go 1.22 or newer (uses method-and-wildcard routing patterns in `net/http`)

## Setup and run

```sh
go mod download
go run .
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Both are configurable through environment variables:

| Variable  | Default    | Description                                      |
|-----------|------------|--------------------------------------------------|
| `ADDR`    | `:8080`    | Address to listen on                             |
| `DB_PATH` | `books.db` | SQLite database file (`:memory:` for ephemeral)  |

```sh
ADDR=127.0.0.1:9000 DB_PATH=/tmp/books.db go run .
```

## Tests

```sh
go test ./...
```

The tests exercise the HTTP handlers end to end against a real SQLite database
(in-memory, plus one on-disk test for persistence across restarts).

## API

All request and response bodies are JSON.

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check (verifies the database) | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books, optional `?author=`      | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

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

| Field    | Type    | Rules                                              |
|----------|---------|----------------------------------------------------|
| `id`     | integer | Assigned by the server; ignored in request bodies  |
| `title`  | string  | Required, must not be blank                        |
| `author` | string  | Required, must not be blank                        |
| `year`   | integer | Optional, defaults to `0`; must not be negative    |
| `isbn`   | string  | Optional, defaults to `""`                         |

Leading and trailing whitespace is trimmed from string fields.

### Behaviour notes

- `GET /books?author=` matches the whole author name, case-insensitively
  (`?author=frank%20herbert` matches `Frank Herbert`; `?author=Frank` does not).
- `PUT` replaces the whole book: `title` and `author` are required, and an
  omitted `year` or `isbn` is reset to its default.
- `POST` sets a `Location` header pointing at the new book.

### Errors

Errors are returned as JSON with an `error` message. Validation failures also
include per-field `details`:

```json
{
  "error": "validation failed",
  "details": { "title": "title is required" }
}
```

| Status | When                                                        |
|--------|-------------------------------------------------------------|
| 400    | Malformed JSON, wrong field type, failed validation, bad ID |
| 404    | No book with that ID                                        |
| 413    | Request body larger than 1 MiB                              |
| 500    | Unexpected database error                                   |
| 503    | `/health` when the database is unreachable                  |

Requests to unknown paths or with unsupported methods get the Go router's
default plain-text 404/405 responses.

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Layout

| File               | Contents                                      |
|--------------------|-----------------------------------------------|
| `main.go`          | Configuration, server startup and shutdown    |
| `handlers.go`      | Routing, request validation, JSON responses   |
| `store.go`         | SQLite schema and queries                     |
| `handlers_test.go` | Integration tests                             |
