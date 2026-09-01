# Book Collection API

A small REST service for managing a book collection, written in Go using only
the standard library's `net/http` router plus the pure-Go SQLite driver
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite). No cgo, no
external services.

## Requirements

- Go 1.22 or newer (the router uses method-and-pattern matching added in 1.22)

## Setup and run

```sh
go mod download
go build -o bookapi .
./bookapi                 # listens on :8080, stores data in ./books.db
```

Or run directly:

```sh
go run .
```

### Configuration

| Flag     | Env var   | Default     | Description                                  |
|----------|-----------|-------------|----------------------------------------------|
| `-addr`  | `ADDR`    | `:8080`     | Listen address                               |
| `-db`    | `DB_PATH` | `books.db`  | SQLite file path; use `:memory:` for ephemeral |

Example: `go run . -addr :9090 -db /tmp/library.db`

The database schema is created automatically on startup. The process shuts
down cleanly on `SIGINT`/`SIGTERM`.

## Run the tests

```sh
go test ./...
```

The suite covers every endpoint end to end against a real temporary SQLite
file: health check, create/get, validation errors, author filtering, update
semantics, delete, ISBN conflicts, bad IDs, and persistence across reopen.

## API

All responses are JSON. Errors have the shape
`{"error": "...", "details": {"field": "reason"}}` (`details` only when
relevant).

| Method | Path                    | Success | Description                              |
|--------|-------------------------|---------|------------------------------------------|
| GET    | `/health`               | 200     | Liveness + database ping                 |
| POST   | `/books`                | 201     | Create a book (sets `Location` header)   |
| GET    | `/books`                | 200     | List books; `?author=` filters by exact author (case-insensitive) |
| GET    | `/books/{id}`           | 200     | Get one book                             |
| PUT    | `/books/{id}`           | 200     | Full replace of a book                   |
| DELETE | `/books/{id}`           | 204     | Delete a book                            |

### Book fields

| Field    | Type    | Rules                                                             |
|----------|---------|-------------------------------------------------------------------|
| `title`  | string  | **required**, trimmed, max 500 chars                              |
| `author` | string  | **required**, trimmed, max 200 chars                              |
| `year`   | integer | optional, 0 to next calendar year                                 |
| `isbn`   | string  | optional; hyphens/spaces stripped; must pass ISBN-10/13 checksum; unique across books |

Responses also include `id`, `created_at`, and `updated_at`.

### Status codes

| Code | When                                                       |
|------|------------------------------------------------------------|
| 400  | Malformed JSON, unknown field, wrong type, or bad `{id}`   |
| 404  | No book with that ID, or unknown route                     |
| 405  | Method not supported on that route                         |
| 409  | ISBN already used by another book                          |
| 415  | `Content-Type` is not `application/json`                   |
| 422  | Validation failed (see `details`)                          |
| 503  | Health check: database unreachable                         |

`PUT` is a full replacement: any optional field omitted from the body is
cleared.

### Examples

```sh
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'

# List, optionally filtered
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Frank%20Herbert'

# Get / update / delete
curl -s localhost:8080/books/1
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -s -i -X DELETE localhost:8080/books/1

# Health
curl -s localhost:8080/health
```

## Layout

| File           | Purpose                                            |
|----------------|----------------------------------------------------|
| `main.go`      | Flags, server setup, graceful shutdown             |
| `handlers.go`  | Routing, JSON decoding, validation, HTTP handlers  |
| `store.go`     | SQLite schema and CRUD operations                  |
| `api_test.go`  | End-to-end HTTP tests and unit tests               |
