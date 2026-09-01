# bookapi

A small REST API for managing a book collection, written in Go using only the
standard library `net/http` router (Go 1.22+ method patterns) and an embedded
SQLite database via the pure-Go driver `modernc.org/sqlite` (no cgo required).

## Requirements

- Go 1.22 or newer (developed with Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `./books.db` by default.
Both can be changed with flags or environment variables:

| Flag    | Env var   | Default    | Description                                  |
|---------|-----------|------------|----------------------------------------------|
| `-addr` | `ADDR`    | `:8080`    | Listen address                               |
| `-db`   | `DB_PATH` | `books.db` | SQLite file path; `:memory:` for ephemeral   |

Example:

```sh
go run . -addr :9090 -db /tmp/books.db
```

Build a binary instead:

```sh
go build -o bookapi .
./bookapi
```

## Test

```sh
go test ./...
```

The tests exercise every endpoint through `httptest` against an in-memory
SQLite database, plus one test that verifies persistence to a file-backed
database across a close and reopen.

## API

All responses are JSON. Errors have the shape `{"error": "..."}`; validation
failures also include a `fields` object mapping field names to messages.

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check (pings the database)        | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books, optional `?author=` filter   | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

### Book payload

```json
{
  "title":  "Dune",            // required
  "author": "Frank Herbert",   // required
  "year":   1965,              // optional, 0..next year
  "isbn":   "978-0441013593"   // optional, 10 or 13 chars ignoring hyphens/spaces
}
```

Unknown fields are rejected. `PUT` is a full replacement: any optional field
omitted from the body is cleared.

### Status codes

- `400 Bad Request` for malformed JSON, wrong field types, unknown fields, or a
  non-numeric / non-positive `{id}`.
- `404 Not Found` when the book does not exist.
- `405 Method Not Allowed` for unsupported methods on a known path.
- `422 Unprocessable Entity` when required fields are missing or values are out
  of range.
- `503 Service Unavailable` from `/health` if the database cannot be reached.

The `?author=` filter is an exact, case-insensitive match.

### Examples

```sh
curl -s localhost:8080/health

curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Frank%20Herbert'
curl -s localhost:8080/books/1

curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe)","author":"Frank Herbert","year":2019}'

curl -s -X DELETE localhost:8080/books/1 -i
```

## Layout

- `main.go` — flag parsing, HTTP server, graceful shutdown, request logging
- `handlers.go` — routes, JSON decoding, validation, response helpers
- `store.go` — SQLite schema and CRUD operations
- `handlers_test.go` — end-to-end handler and persistence tests
