# Book Collection API

A small REST API for managing a collection of books, written in Go using only
the standard library's `net/http` router and an embedded SQLite database
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
driver, so **no C compiler or cgo is needed**).

## Requirements

- Go 1.26 or newer (the router's method/path patterns need Go 1.22+)

## Setup and run

```sh
go build -o bookapi .   # dependencies are fetched automatically
./bookapi               # listens on :8080, stores data in ./books.db
```

Or without building a binary: `go run .`

Configuration (flags take precedence over environment variables):

| Flag    | Environment | Default    | Meaning                                  |
|---------|-------------|------------|------------------------------------------|
| `-addr` | `ADDR`      | `:8080`    | Listen address. `PORT` sets just the port. |
| `-db`   | `DB_PATH`   | `books.db` | SQLite database file (created if missing). |

```sh
PORT=9000 DB_PATH=/var/lib/books/books.db ./bookapi
./bookapi -addr 127.0.0.1:9000 -db :memory:    # throwaway in-memory database
```

The server shuts down gracefully on `SIGINT`/`SIGTERM`.

## Run the tests

```sh
go test ./...
go test -race ./...     # recommended
```

The tests use real SQLite databases (temporary files or in-memory), and the API
tests exercise the service over real HTTP with `httptest`.

## API

All request and response bodies are JSON. A book looks like:

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719" }
```

| Field    | Type    | Rules                                                              |
|----------|---------|--------------------------------------------------------------------|
| `id`     | integer | Assigned by the server; never reused. Ignored if sent by a client. |
| `title`  | string  | **Required**, not blank, at most 500 characters.                   |
| `author` | string  | **Required**, not blank, at most 255 characters.                   |
| `year`   | integer | Optional, 0–9999. `0` means unknown.                               |
| `isbn`   | string  | Optional, free-form, at most 32 characters. Not required to be unique. |

Leading and trailing whitespace in strings is trimmed.

### Endpoints

| Method | Path           | Description                     | Success            |
|--------|----------------|---------------------------------|--------------------|
| POST   | `/books`       | Create a book                   | `201` + book, `Location` header |
| GET    | `/books`       | List books (`?author=` filter)  | `200` + array (`[]` when empty) |
| GET    | `/books/{id}`  | Get one book                    | `200` + book       |
| PUT    | `/books/{id}`  | Replace a book (full update)    | `200` + book       |
| DELETE | `/books/{id}`  | Delete a book                   | `204`, no body     |
| GET    | `/health`      | Health check (pings the database) | `200` `{"status":"ok"}` |

`PUT` replaces the whole book, so it needs `title` and `author` like `POST`
does, and omitted optional fields are reset to their defaults.

`GET /books?author=George%20Orwell` returns only that author's books. The match
is an exact, case-insensitive comparison of the whole author name (not a
substring search); an empty `?author=` applies no filter. Books are returned in
the order they were created.

### Errors

Every error uses the same shape:

```json
{ "error": "validation failed", "details": { "title": "is required" } }
```

`details` appears only for validation failures and maps field names to
problems. Status codes:

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| `400`  | Validation failure, malformed/empty JSON, wrong field types, or a non-numeric / non-positive `{id}` |
| `404`  | No such book, or unknown route                                       |
| `405`  | Known route, unsupported method (includes an `Allow` header)         |
| `413`  | Request body larger than 1 MiB                                       |
| `500`  | Unexpected server error (details are logged, not returned)           |
| `503`  | `/health` only: the database is unreachable                          |

### Example session

```sh
# Create
curl -i -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List, filtered by author
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'
curl -i -X DELETE localhost:8080/books/1

# Validation error
curl -i -X POST localhost:8080/books -d '{"year":1965}'
# HTTP/1.1 400 Bad Request
# {"error":"validation failed","details":{"author":"is required","title":"is required"}}

# Health
curl localhost:8080/health
```

## Project layout

```
main.go                  entry point: config, wiring, graceful shutdown
internal/book/           Book model, input validation, ErrNotFound
internal/store/          SQLite persistence (schema is created on startup)
internal/api/            HTTP routing, handlers, JSON helpers, logging/recovery middleware
```

## Design notes

- **Storage:** one `books` table with an auto-incrementing primary key
  (`AUTOINCREMENT`, so IDs are not recycled after deletes) and a
  case-insensitive index on `author`. On-disk databases use WAL mode and a 5 s
  busy timeout so concurrent requests don't fail with "database is locked".
- **Layering:** the `api` package depends on a small `BookStore` interface, so
  handlers are tested against both the real SQLite store and stub stores that
  simulate failures.
- **Errors:** internal error details are logged server-side and never sent to
  clients.
