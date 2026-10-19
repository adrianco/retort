# Book Collection REST API

A REST API for managing a book collection, written in Go (Gin) with a
SQLite database (pure-Go driver, no CGO required).

## Endpoints

| Method | Path         | Description                                  | Success | Errors      |
|--------|--------------|----------------------------------------------|---------|-------------|
| GET    | `/`          | Service info                                 | 200     |             |
| GET    | `/health`    | Health check (verifies DB connectivity)      | 200     | 503         |
| POST   | `/books`     | Create a book                                | 201     | 400, 500    |
| GET    | `/books`     | List all books (`?author=` filter)           | 200     | 500         |
| GET    | `/books/{id}`| Get a book by ID                             | 200     | 400, 404    |
| PUT    | `/books/{id}`| Update a book (full replacement)             | 200     | 400, 404    |
| DELETE | `/books/{id}`| Delete a book                                | 204     | 400, 404    |

Unknown routes return a JSON `404`. All errors are JSON: `{"error": "..."}`.

### Book fields

- `id` — auto-assigned integer (read-only)
- `title` — **required** (non-empty)
- `author` — **required** (non-empty)
- `year` — optional, non-negative integer (`0` = not set)
- `isbn` — optional string

The `?author=` filter on `GET /books` is a case-insensitive exact match
(e.g. `?author=frank herbert` matches `Frank Herbert`).

## Setup

Requires Go 1.22+ (tested with Go 1.26). No C compiler needed — the
SQLite driver is pure Go (`modernc.org/sqlite`).

```sh
go mod tidy        # fetch dependencies
```

## Run

```sh
go run .                       # listens on :8000, uses ./books.db
go run . -port 9000 -db my.db  # custom port and database file
```

The database file is created automatically on first start.

## Examples

```sh
curl http://localhost:8000/health
# {"status":"ok"}

curl -X POST http://localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
# 201 -> {"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}

curl http://localhost:8000/books
curl 'http://localhost:8000/books?author=Frank%20Herbert'
curl http://localhost:8000/books/1

curl -X PUT http://localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"978-0441478125"}'

curl -X DELETE http://localhost:8000/books/1
# 204 (no body)
```

## Tests

```sh
go test ./...
```

The suite covers the full HTTP API (health, create + validation, list +
author filter, get, update, delete, unknown routes) plus unit tests for
the SQLite store (CRUD round-trip, filtering, not-found handling) and the
validation rules.

## Project layout

- `main.go` — entry point: flags, server, graceful shutdown
- `handlers.go` — Gin routes and HTTP handlers, input validation
- `db.go` — SQLite store (schema, CRUD)
- `handlers_test.go` — HTTP integration tests
- `db_test.go` — store and validation unit tests
