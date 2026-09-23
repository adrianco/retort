# Book Collection API (Go)

A REST API for managing a book collection. Built with the Go standard library
`net/http` router (Go 1.22+ method/path patterns) and SQLite via the pure-Go
driver [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), so you
don't need cgo or a C compiler.

## Requirements

- Go 1.26 or newer (see `go.mod`)

## Setup and run

```bash
go mod download          # fetch dependencies
go run .                 # listens on :8080, stores data in ./books.db
```

Or build a binary:

```bash
go build -o bookapi .
./bookapi -addr :9000 -db /path/to/books.db
```

| Flag    | Env var   | Default    | Description               |
|---------|-----------|------------|---------------------------|
| `-addr` | `ADDR`    | `:8080`    | HTTP listen address       |
| `-db`   | `DB_PATH` | `books.db` | SQLite database file path |

The schema is created automatically on startup. The server shuts down cleanly on SIGINT/SIGTERM.

## Run tests

```bash
go test -race ./...
```

Each test gets its own temporary SQLite file. The tests cover the full CRUD
lifecycle, author filtering, validation errors, 404s and malformed IDs, the
health check, and data persisting after the database is reopened.

## API

| Method | Path          | Success | Description                                  |
|--------|---------------|---------|----------------------------------------------|
| GET    | `/health`     | 200     | Health check (pings the database; 503 if it's down) |
| POST   | `/books`      | 201     | Create a book (sets the `Location` header)   |
| GET    | `/books`      | 200     | List books; `?author=` filters by exact author name, case-insensitive |
| GET    | `/books/{id}` | 200     | Get a book                                   |
| PUT    | `/books/{id}` | 200     | Replace a book's fields                      |
| DELETE | `/books/{id}` | 204     | Delete a book                                |

### Book payload

```json
{ "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593" }
```

Validation rules:
- `title` (required, max 500 characters) and `author` (required, max 300 characters). Surrounding whitespace is trimmed.
- `year` is optional and must be between 0 and next year.
- `isbn` is optional. It must be 10 or 13 digits; hyphens and spaces are allowed, and an ISBN-10 may end in `X`. Only the format is checked, not the checksum.
- Unknown fields, malformed JSON, and wrong types are rejected.

### Errors

Error responses are JSON:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

Status codes: `400` for invalid input or ID, `404` if the book doesn't exist,
`405` for an unsupported method, `500` for internal errors.

### Examples

```bash
curl -X POST localhost:8080/books -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl 'localhost:8080/books?author=Frank%20Herbert'
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -H 'Content-Type: application/json' \
     -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -X DELETE localhost:8080/books/1
curl localhost:8080/health
```
