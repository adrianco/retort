# Books API

A REST API for managing a book collection, written in Go with the standard
library HTTP router and an embedded SQLite database.

- Go 1.22+ (developed with Go 1.26)
- Storage: SQLite via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), pure Go (no cgo or C toolchain needed)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current directory.

Configuration via environment variables:

| Variable     | Default    | Description                          |
|--------------|------------|--------------------------------------|
| `BOOKS_ADDR` | `:8080`    | Address to listen on                 |
| `BOOKS_DB`   | `books.db` | Path to the SQLite database file     |

Example:

```sh
BOOKS_ADDR=:9000 BOOKS_DB=/tmp/books.db go run .
```

Build a binary instead:

```sh
go build -o booksapi . && ./booksapi
```

## Test

```sh
go test ./...
```

Tests run against an in-memory SQLite database and exercise the HTTP handlers directly.

## API

All request and response bodies are JSON. Errors are returned as `{"error": "..."}`.

### Book fields

| Field    | Type    | Required | Notes                                  |
|----------|---------|----------|----------------------------------------|
| `id`     | integer | —        | Assigned by the server (read-only)     |
| `title`  | string  | yes      | Must not be blank                      |
| `author` | string  | yes      | Must not be blank                      |
| `year`   | integer | yes      | Between 1450 and next calendar year    |
| `isbn`   | string  | no       | Free text, defaults to `""`            |

### Endpoints

| Method   | Path          | Success | Description                              |
|----------|---------------|---------|------------------------------------------|
| `POST`   | `/books`      | `201`   | Create a book                            |
| `GET`    | `/books`      | `200`   | List books; supports `?author=` filter   |
| `GET`    | `/books/{id}` | `200`   | Get one book                             |
| `PUT`    | `/books/{id}` | `200`   | Replace a book's fields                  |
| `DELETE` | `/books/{id}` | `204`   | Delete a book                            |
| `GET`    | `/health`     | `200`   | Health check (`503` if the DB is unreachable) |

`PUT` takes the full book representation (all of `title`, `author`, `year`, `isbn`);
it is a full replacement, not a partial patch.

`?author=` matches the author name exactly (case-sensitive), e.g. `?author=Frank%20Herbert`.

### Status codes

| Code  | When                                                              |
|-------|-------------------------------------------------------------------|
| `400` | Malformed JSON, unknown fields, empty body, non-integer/invalid ID |
| `404` | Book not found                                                    |
| `422` | Validation failed; response includes a `fields` map of problems   |
| `500` | Unexpected server error                                           |
| `503` | Health check failed                                               |

### Examples

Create:

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```json
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}
```

List by author:

```sh
curl 'localhost:8080/books?author=Frank%20Herbert'
```

Update:

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

Delete:

```sh
curl -i -X DELETE localhost:8080/books/1
```

Validation error:

```json
{"error":"validation failed","fields":{"title":"title is required"}}
```

## Project layout

| File            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `main.go`       | Entry point, configuration, graceful shutdown        |
| `handlers.go`   | Routes, request parsing, validation, JSON responses   |
| `store.go`      | SQLite persistence and schema migration              |
| `books_test.go` | HTTP-level tests against an in-memory database       |
