# Book Collection API

A REST API for managing a book collection, written in Go using only the standard
library router (`net/http`) and an embedded SQLite database.

## Requirements

- Go 1.26 or newer (required by the SQLite driver; developed and tested with Go 1.26.6)
- No C toolchain needed: the SQLite driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)) is pure Go.

## Setup

```sh
go mod download
```

## Run

```sh
go run ./cmd/bookapi
```

By default the server listens on `:8080` and stores data in `books.db` in the
current directory. Both can be changed with flags or environment variables:

| Flag    | Env       | Default    | Purpose                       |
|---------|-----------|------------|-------------------------------|
| `-addr` | `ADDR`    | `:8080`    | HTTP listen address           |
| `-db`   | `DB_PATH` | `books.db` | Path to the SQLite database   |

```sh
ADDR=:9000 DB_PATH=/var/lib/bookapi/books.db go run ./cmd/bookapi
```

To build a binary:

```sh
go build -o bookapi ./cmd/bookapi
./bookapi -addr :8080 -db books.db
```

The server shuts down gracefully on `Ctrl-C` or `SIGTERM`.

## Test

```sh
go test ./...
go test -race ./...   # optional, checks for data races
```

Tests cover validation rules, the SQLite store, and every HTTP endpoint. Each
test uses its own temporary database, so no setup is needed and nothing is left
behind.

## API

All request and response bodies are JSON. Errors are returned as
`{"error": "..."}`; validation failures also include a `fields` object.

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441172719"
}
```

| Field    | Type    | Required | Notes                                                              |
|----------|---------|----------|--------------------------------------------------------------------|
| `title`  | string  | yes      | Whitespace is trimmed. Must not be empty.                          |
| `author` | string  | yes      | Whitespace is trimmed. Must not be empty.                          |
| `year`   | integer | no       | Publication year. `0` or omitted means unknown. Otherwise 1 to next year. |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 with a valid check digit. Hyphens and spaces are removed when stored. `""` or omitted means unknown. |

`id` is assigned by the server and cannot be set by clients.

### Endpoints

| Method   | Path          | Success                          | Description                                 |
|----------|---------------|----------------------------------|---------------------------------------------|
| `POST`   | `/books`      | `201 Created` + `Location` header | Create a book                               |
| `GET`    | `/books`      | `200 OK`                         | List all books. Filter with `?author=`.     |
| `GET`    | `/books/{id}` | `200 OK`                         | Get one book                                |
| `PUT`    | `/books/{id}` | `200 OK`                         | Replace a book (full update)                |
| `DELETE` | `/books/{id}` | `204 No Content`                 | Delete a book                               |
| `GET`    | `/health`     | `200 OK`                         | Liveness check, verifies the database responds |

`PUT` replaces the whole book, so `title` and `author` are required again, and
omitted `year` or `isbn` values are cleared.

`?author=` matches case-insensitively against the full author name
(`?author=frank herbert` matches `Frank Herbert`, but `?author=herbert` does not).

### Status codes

| Code  | When                                                                      |
|-------|---------------------------------------------------------------------------|
| `200` | Success                                                                   |
| `201` | Book created                                                              |
| `204` | Book deleted                                                              |
| `400` | Malformed JSON, unknown field, body too large (>1 MiB), validation error, or an `{id}` that is not a positive integer |
| `404` | No book with that id                                                      |
| `405` | Method not allowed on a known path (set by the router)                    |
| `500` | Unexpected server or database error (details are logged, not returned)    |
| `503` | `/health` only: the database is not reachable                             |

### Examples

```sh
# Health
curl -i localhost:8080/health

# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}'

# List, and filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
curl -i -X DELETE localhost:8080/books/1
```

## Project layout

```
.
├── book.go            # Book types, input cleaning, and validation (incl. ISBN check digits)
├── store.go           # SQLite persistence
├── server.go          # HTTP routes, handlers, and JSON helpers
├── cmd/bookapi/main.go  # Entrypoint: config, server, graceful shutdown
├── book_test.go       # Validation unit tests
├── store_test.go      # Store integration tests against a real SQLite file
└── api_test.go        # End-to-end HTTP tests through the handler
```

## Design notes

- **SQLite via a pure-Go driver** keeps the build free of cgo. The connection
  pool is limited to one connection, since SQLite serialises writes anyway.
- **Go 1.22+ `ServeMux` patterns** (`GET /books/{id}`) handle routing, so there
  are no third-party routers.
- **Strict JSON decoding**: unknown fields are rejected so typos in field names
  fail loudly rather than being silently dropped.
- The schema is created on startup with `CREATE TABLE IF NOT EXISTS`. There is
  no migration tool yet.
