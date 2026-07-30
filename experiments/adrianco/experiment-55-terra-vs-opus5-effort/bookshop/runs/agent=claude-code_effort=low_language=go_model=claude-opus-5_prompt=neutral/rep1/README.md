# Book Collection API

A small REST API for managing a book collection, written in Go using the standard
library `net/http` router and an embedded SQLite database
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite) — pure Go, no cgo required).

## Requirements

- Go 1.22 or newer (uses method+wildcard `ServeMux` patterns)

## Setup and run

```sh
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Both are configurable:

```sh
ADDR=:9000 BOOKS_DB=/var/lib/books.db go run .
```

To build a binary:

```sh
go build -o bookapi .
./bookapi
```

## Tests

```sh
go test ./...
```

The tests in `server_test.go` run against the full HTTP handler backed by an
in-memory SQLite database, covering create/read, validation errors, the author
filter, update/delete, 404 handling, and the health check.

## API

All responses are JSON. Errors have the shape `{"error": "message"}`.

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness check (pings the DB) | `200` |
| `POST` | `/books` | Create a book | `201` |
| `GET` | `/books` | List books; `?author=` filters by exact author | `200` |
| `GET` | `/books/{id}` | Fetch one book | `200` |
| `PUT` | `/books/{id}` | Replace a book | `200` |
| `DELETE` | `/books/{id}` | Delete a book | `204` |

### Book object

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### Validation

- `title` and `author` are required and must be non-blank (surrounding
  whitespace is trimmed).
- `year`, if given as non-zero, must be between 1 and 3000.
- `isbn` and `year` are optional.
- Unknown JSON fields are rejected.

### Status codes

- `400 Bad Request` — malformed JSON, failed validation, or a non-numeric `{id}`
- `404 Not Found` — no book with that ID
- `500 Internal Server Error` — database failure
- `503 Service Unavailable` — `/health` when the database is unreachable

## Examples

```sh
curl -s localhost:8080/health

curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -s 'localhost:8080/books?author=Frank%20Herbert'

curl -s localhost:8080/books/1

curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8080/books/1
```

## Layout

| File | Contents |
| --- | --- |
| `main.go` | Entrypoint, configuration, HTTP server setup |
| `server.go` | Routes, request decoding, validation, JSON responses |
| `store.go` | SQLite schema and CRUD data access |
| `server_test.go` | Integration tests over the HTTP handler |
