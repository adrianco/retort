# Book Collection API

A small REST service for managing a book collection, written in Go using only
the standard library `net/http` router and an embedded SQLite database
(via the pure-Go `modernc.org/sqlite` driver, so no cgo or system SQLite is required).

## Requirements

- Go 1.26 or newer

## Setup

```sh
go mod download
```

## Run

```sh
go run ./cmd/server
```

The server listens on `:8080` and stores data in `books.db` in the working
directory. Both can be overridden by flag or environment variable:

| Flag     | Env var   | Default    | Description                    |
|----------|-----------|------------|--------------------------------|
| `-addr`  | `ADDR`    | `:8080`    | Listen address                 |
| `-db`    | `DB_PATH` | `books.db` | SQLite database file           |

Example:

```sh
go run ./cmd/server -addr :9090 -db /tmp/library.db
```

Build a standalone binary with `go build -o bookapi ./cmd/server`.

## Test

```sh
go test ./...
```

The tests run the real handler stack against a temporary SQLite database, so
they cover routing, validation, persistence, and error mapping end to end.

## API

All responses are JSON. Errors have the shape
`{"error": "<message>", "fields": {"<field>": "<problem>"}}` where `fields`
is only present for validation failures.

### Book resource

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

`title` and `author` are required. `year` and `isbn` are optional; `isbn`
must be a 10- or 13-digit ISBN (hyphens allowed) and is unique across books.

### Endpoints

| Method   | Path                  | Description                              | Success |
|----------|-----------------------|------------------------------------------|---------|
| `GET`    | `/health`             | Health check (verifies DB connectivity)  | `200`   |
| `POST`   | `/books`              | Create a book                            | `201`   |
| `GET`    | `/books`              | List books; `?author=` filters by author | `200`   |
| `GET`    | `/books/{id}`         | Get one book                             | `200`   |
| `PUT`    | `/books/{id}`         | Replace a book (full update)             | `200`   |
| `DELETE` | `/books/{id}`         | Delete a book                            | `204`   |

Error status codes:

| Status | When                                                   |
|--------|--------------------------------------------------------|
| `400`  | Malformed JSON, unknown fields, or a non-numeric `id`  |
| `404`  | No book with that `id`                                 |
| `405`  | Unsupported method on a known path                     |
| `409`  | `isbn` already belongs to another book                 |
| `413`  | Request body larger than 1 MiB                         |
| `422`  | Validation failed (see `fields` in the response)       |
| `503`  | Health check: database unreachable                     |

### Examples

```sh
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}'

# List, optionally filtered by author (case-insensitive exact match)
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=Frank+Herbert'

# Get one
curl -s localhost:8080/books/1

# Update (full replacement)
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'

# Delete
curl -s -X DELETE localhost:8080/books/1 -o /dev/null -w '%{http_code}\n'

# Health
curl -s localhost:8080/health
```

## Project layout

```
cmd/server/        main package: flags, server startup, graceful shutdown
internal/store/    SQLite persistence layer and its tests
internal/api/      HTTP handlers, validation, JSON helpers, and API tests
```
