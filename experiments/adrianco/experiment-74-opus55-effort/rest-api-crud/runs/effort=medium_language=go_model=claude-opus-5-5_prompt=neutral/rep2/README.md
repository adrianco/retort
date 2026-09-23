# Book Collection API (Go)

A REST API for managing a book collection. It is built with Go's standard `net/http` router (Go 1.22+ method and path patterns) and stores data in SQLite through [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go driver that needs no CGO or C compiler.

## Requirements

- Go 1.22 or newer (developed with Go 1.26)

## Setup & run

```bash
go mod download
go run .                      # listens on :8080, database file ./books.db
```

Configuration (environment variables):

| Variable  | Default    | Description               |
|-----------|------------|---------------------------|
| `ADDR`    | `:8080`    | Listen address            |
| `DB_PATH` | `books.db` | SQLite database file path |

Build a binary: `go build -o bookapi . && ./bookapi`

## Tests

```bash
go test ./...
```

The tests start the full HTTP handler against a temporary SQLite database. They cover the CRUD lifecycle, the author filter, validation errors, 404 and 400 handling, the health check, persistence after reopening the database, and ISBN checks.

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check (pings the database)    | 200     |
| POST   | `/books`      | Create a book                        | 201 (+ `Location` header) |
| GET    | `/books`      | List books; optional `?author=` filter (exact match, case-insensitive) | 200 |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book's fields              | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

### Book payload

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

Validation rules:
- `title` (required, max 500 chars) and `author` (required, max 200 chars). Surrounding whitespace is trimmed.
- `year` (optional) must be between 0 and next year.
- `isbn` (optional) must have 10 or 13 digits. Hyphens and spaces are allowed, and an ISBN-10 may end in `X`.
- Unknown fields and malformed JSON are rejected.

### Error responses

| Status | When |
|--------|------|
| 400 | Malformed JSON, unknown fields, or an invalid ID |
| 404 | The book does not exist |
| 405 | Unsupported method |
| 422 | Validation failed; the response lists the errors for each field |
| 500 | Internal error |

Example 422 body:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

### Examples

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
curl -X DELETE localhost:8080/books/1
```

## Project layout

- `main.go`: configuration, server startup, and graceful shutdown
- `handlers.go`: routes, input validation, and JSON responses
- `store.go`: SQLite storage (schema and CRUD queries)
- `main_test.go`: integration tests
