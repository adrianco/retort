# Book Collection REST API (Go)

A small REST API for managing a book collection, written in Go with the
standard library `net/http` router (Go 1.22+ method/wildcard patterns) and a
pure-Go SQLite driver (`modernc.org/sqlite` — no CGO required).

## Endpoints

| Method | Path           | Description                                  | Success |
|--------|----------------|----------------------------------------------|---------|
| GET    | `/health`      | Health check                                 | 200     |
| GET    | `/`            | Service info + endpoint list                 | 200     |
| POST   | `/books`       | Create a book (`title`, `author` required; `year`, `isbn` optional) | 201 |
| GET    | `/books`       | List all books (`?author=` filter, case-insensitive exact match) | 200 |
| GET    | `/books/{id}`  | Get a single book                            | 200     |
| PUT    | `/books/{id}`  | Update a book (full replacement)             | 200     |
| DELETE | `/books/{id}`  | Delete a book                                | 204     |

Error responses are JSON: `{"error": "..."}` with status 400 (validation /
bad input), 404 (not found), or 500 (internal).

## Setup

Requires Go 1.22+ (tested with Go 1.26).

```sh
go mod download   # fetch the single dependency (modernc.org/sqlite)
```

## Run

```sh
go run .
```

The server listens on port 8000 and stores data in `books.db` in the current
directory. Configuration via environment variables:

- `PORT` — listen port (default `8000`)
- `BOOKS_DB` — path to the SQLite file (default `books.db`)

## Examples

```sh
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'
# 201, returns the created book with its id and a Location header

curl 'http://localhost:8000/books?author=Donovan%20%26%20Kernighan'
curl http://localhost:8000/books/1
curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language (2nd ed.)","author":"Donovan & Kernighan","year":2024}'
curl -X DELETE http://localhost:8000/books/1   # 204
```

## Tests

```sh
go test ./...
```

The suite covers the health check, creation (including validation of
required fields, year range, and malformed JSON), listing with the author
filter, single-book retrieval, updates (including 404 and validation),
deletes (including 404 and invalid ids), plus a direct unit test of the
validation logic. Each test runs against a throwaway database in a temp dir.

## Files

- `main.go` — entry point: DB open, env config, server startup
- `server.go` — HTTP handlers, routing, validation, JSON helpers
- `store.go` — schema init and SQL access helpers
- `server_test.go` — integration + unit tests
