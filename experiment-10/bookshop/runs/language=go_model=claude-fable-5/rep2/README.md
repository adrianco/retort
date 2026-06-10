# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router (Go 1.22+ method/path patterns) and SQLite via the
pure-Go [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver
(no cgo required).

## Requirements

- Go 1.22 or newer

## Setup & Run

```sh
go mod download   # fetch dependencies (first run only)
go run .          # starts on :8080, creates books.db in the current directory
```

Configuration via environment variables:

| Variable   | Default    | Description                  |
|------------|------------|------------------------------|
| `ADDR`     | `:8080`    | Listen address               |
| `BOOKS_DB` | `books.db` | Path to the SQLite database  |

## Running tests

```sh
go test ./...
```

Tests spin up the full HTTP stack (`httptest.Server`) against a temporary
SQLite database, covering create/get, validation errors, author filtering,
update, delete, invalid IDs, and the health check.

## API

| Method | Path          | Description                                |
|--------|---------------|--------------------------------------------|
| GET    | `/health`     | Health check                                |
| POST   | `/books`      | Create a book                               |
| GET    | `/books`      | List all books; supports `?author=` filter  |
| GET    | `/books/{id}` | Get a book by ID                            |
| PUT    | `/books/{id}` | Update a book (full replacement)            |
| DELETE | `/books/{id}` | Delete a book                               |

A book looks like:

```json
{ "id": 1, "title": "Sun Performance and Tuning", "author": "Adrian Cockcroft", "year": 1998, "isbn": "978-0130952493" }
```

`title` and `author` are required (non-blank); `year` and `isbn` are optional.
Unknown JSON fields are rejected.

### Status codes

- `200 OK` — successful get/list/update
- `201 Created` — book created
- `204 No Content` — book deleted
- `400 Bad Request` — invalid JSON, failed validation, or malformed ID
- `404 Not Found` — no book with that ID
- `500 Internal Server Error` — unexpected database failure
- `503 Service Unavailable` — health check failed

Errors are returned as `{"error": "message"}`.

### Examples

```sh
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Microservices","author":"Adrian Cockcroft","year":2016}'

# List, optionally filtered by author (exact match)
curl -s 'localhost:8080/books?author=Adrian%20Cockcroft'

# Get / update / delete by ID
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Microservices, 2nd Ed","author":"Adrian Cockcroft","year":2018}'
curl -s -X DELETE localhost:8080/books/1 -i

# Health check
curl -s localhost:8080/health
```

## Project layout

- `main.go` — entry point: config, DB open, HTTP server
- `store.go` — `Book` model and SQLite persistence layer
- `handlers.go` — HTTP routing, validation, and JSON handlers
- `handlers_test.go` — integration tests over the full HTTP stack
