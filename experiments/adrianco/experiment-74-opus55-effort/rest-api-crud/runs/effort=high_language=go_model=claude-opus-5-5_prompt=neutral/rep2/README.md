# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` router (Go 1.22+ method/path patterns) and SQLite
for storage via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no cgo or C toolchain is needed.

## Requirements

- Go 1.25 or newer (see `go.mod`)

## Setup and run

```sh
go mod download        # fetch dependencies
go run .               # starts on :8080 using ./books.db
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

Configuration is through environment variables:

| Variable  | Default    | Description                                      |
|-----------|------------|--------------------------------------------------|
| `PORT`    | `8080`     | TCP port to listen on                            |
| `DB_PATH` | `books.db` | SQLite database file (use `:memory:` for ephemeral) |

The schema is created automatically on startup. The server shuts down cleanly
on SIGINT or SIGTERM.

## Running tests

```sh
go test ./...
go test -race -v ./...   # verbose, with the race detector
```

The tests in `api_test.go` run each case against an in-memory database through
`httptest`. They cover the full CRUD lifecycle, the author filter, input
validation, malformed JSON, invalid and missing IDs, the health check, and
data persisting across a store restart.

## API

All responses are JSON (`Content-Type: application/json`) except `204 No Content`.

### Book object

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

| Field    | Type    | Rules                                                     |
|----------|---------|-----------------------------------------------------------|
| `title`  | string  | **required**, non-blank, at most 500 characters            |
| `author` | string  | **required**, non-blank, at most 200 characters            |
| `year`   | integer | optional (default 0), between 0 and next year      |
| `isbn`   | string  | optional, at most 32 characters                          |

Surrounding whitespace is trimmed from string fields. The server assigns `id`;
if a request body includes one, it is ignored.

### Endpoints

| Method   | Path          | Description                                  | Success |
|----------|---------------|----------------------------------------------|---------|
| `GET`    | `/health`     | Health check (also pings the database)       | `200`   |
| `POST`   | `/books`      | Create a book                                | `201` + `Location` header |
| `GET`    | `/books`      | List all books, ordered by id                | `200`   |
| `GET`    | `/books?author=Name` | List books by author (exact match, case-insensitive) | `200` |
| `GET`    | `/books/{id}` | Get one book                                 | `200`   |
| `PUT`    | `/books/{id}` | Replace a book's fields (same rules as create) | `200` |
| `DELETE` | `/books/{id}` | Delete a book                                | `204`   |

### Errors

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Malformed or empty JSON, failed validation, non-positive or non-numeric id |
| `404`  | No book with that id                                               |
| `405`  | Method not supported for the path                                    |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected database error (details are logged, not returned)         |
| `503`  | `/health` when the database is unreachable                           |

Error body:

```json
{ "error": "validation failed", "details": { "title": "title is required" } }
```

### Examples

```sh
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl 'localhost:8080/books?author=frank%20herbert'
curl localhost:8080/books/1

curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```

## Project layout

| File            | Purpose                                         |
|-----------------|-------------------------------------------------|
| `main.go`       | Configuration, HTTP server, graceful shutdown   |
| `handlers.go`   | Routes, request decoding, JSON responses        |
| `validation.go` | `BookInput` payload and validation rules        |
| `store.go`      | SQLite schema and CRUD queries                  |
| `api_test.go`   | Integration tests                               |
