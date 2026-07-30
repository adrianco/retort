# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library's `net/http` router (Go 1.22+ method/pattern routing) with
SQLite persistence via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)
— a pure-Go driver, so **no cgo or C toolchain is required**.

## Requirements

- Go 1.22 or newer (developed against 1.26)

## Setup and run

```bash
go mod download
go run .
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Both are configurable:

```bash
ADDR=:9000 DB_PATH=/tmp/mybooks.db go run .
```

To build a binary:

```bash
go build -o bookapi .
./bookapi
```

## Tests

```bash
go test ./...
```

Tests run against an in-memory SQLite database and exercise the full HTTP stack
via `httptest` — health check, create/read/update/delete round-trips, the author
filter, validation failures, and 400/404 error paths.

## API

| Method | Path | Description | Success |
|---|---|---|---|
| `GET` | `/health` | Health check | `200 {"status":"ok"}` |
| `POST` | `/books` | Create a book | `201` + book |
| `GET` | `/books` | List books, optional `?author=` exact-match filter | `200` + array |
| `GET` | `/books/{id}` | Fetch one book | `200` + book |
| `PUT` | `/books/{id}` | Replace a book | `200` + book |
| `DELETE` | `/books/{id}` | Delete a book | `204`, no body |

### Book representation

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

`title` and `author` are required and must be non-blank (surrounding whitespace
is trimmed). `year` and `isbn` are optional and default to `0` / `""`.

### Errors

Errors return the appropriate status with a JSON body of `{"error": "..."}`.

- `400 Bad Request` — malformed JSON, unknown fields, missing/blank `title` or
  `author`, or a non-numeric `{id}`
- `404 Not Found` — no book with that ID
- `500 Internal Server Error` — database failure

## Examples

```bash
curl -s localhost:8080/health

curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

curl -s 'localhost:8080/books?author=Frank%20Herbert'

curl -s localhost:8080/books/1

curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"9780441013593"}'

curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8080/books/1
```

## Layout

- `main.go` — entrypoint, configuration, server startup
- `server.go` — routing, JSON encoding/decoding, validation, status codes
- `store.go` — SQLite schema and CRUD queries
- `server_test.go` — integration tests over the HTTP handlers
