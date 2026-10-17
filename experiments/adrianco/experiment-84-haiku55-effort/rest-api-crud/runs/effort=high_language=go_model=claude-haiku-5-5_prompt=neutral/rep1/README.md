# Book Collection API

A small REST service for managing a book collection. Written in Go using the
standard library HTTP server and router, with data stored in SQLite. The SQLite
driver is pure Go, so no C compiler or CGO is needed.

## Requirements

- Go 1.26 or newer (the SQLite driver's `go.mod` requires it)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory. Both can be changed with flags or environment variables:

| Flag    | Environment    | Default    | Purpose                    |
|---------|----------------|------------|----------------------------|
| `-addr` | `BOOKS_ADDR`   | `:8080`    | HTTP listen address        |
| `-db`   | `BOOKS_DB`     | `books.db` | Path to the SQLite file    |

The directory containing the database file must already exist. The file itself
is created on first start. The server shuts down cleanly on `Ctrl-C` or
`SIGTERM`.

To build a binary instead:

```sh
go build -o bookservice .
./bookservice -addr :9000 -db ./data/books.db
```

## Test

```sh
go test ./...
```

The suite covers:

- **`internal/book`**: validation rules, including required fields, length
  limits, year range, and ISBN-10/13 checksums.
- **`internal/store`**: SQLite CRUD, the author filter, not-found handling, and
  persistence across reopening the database.
- **`internal/api`**: end-to-end HTTP tests against a temporary database for
  every endpoint, status code, and error path.

## API

All request and response bodies are JSON. Errors have the shape
`{"error": "<message>"}`. Validation failures also include a `details` object
that maps each invalid field to its reason.

### Book resource

| Field    | Type    | Required | Notes                                                       |
|----------|---------|----------|-------------------------------------------------------------|
| `id`     | integer | —        | Assigned by the server. Any `id` sent in a request is ignored. |
| `title`  | string  | yes      | Trimmed. 1–500 characters.                                  |
| `author` | string  | yes      | Trimmed. 1–300 characters.                                  |
| `year`   | integer | no       | Publication year. Omit or send `0` if unknown. Otherwise 1000 through next year. |
| `isbn`   | string  | no       | ISBN-10 or ISBN-13 with a valid check digit. Hyphens and spaces are allowed on input and are stripped when stored. |

### Endpoints

| Method   | Path         | Success | Description                                  |
|----------|--------------|---------|----------------------------------------------|
| `POST`   | `/books`     | `201`   | Create a book. Returns it with `Location` set. |
| `GET`    | `/books`     | `200`   | List books in insertion order. Supports `?author=`. |
| `GET`    | `/books/{id}`| `200`   | Get one book.                                |
| `PUT`    | `/books/{id}`| `200`   | Replace a book. Title and author are required, as on create. |
| `DELETE` | `/books/{id}`| `204`   | Delete a book. No response body.             |
| `GET`    | `/health`    | `200`   | Liveness check. Returns `503` if the database cannot be reached. |

**Author filter.** `GET /books?author=Frank Herbert` returns only books whose
author matches, ignoring case. The match is exact, not a substring match. An
empty `?author=` is treated the same as omitting the parameter.

### Status codes

| Code  | When                                                              |
|-------|-------------------------------------------------------------------|
| `400` | Malformed JSON, a missing or invalid field, or an `{id}` that is not a positive integer |
| `404` | No book with that `id`, or an unknown path                        |
| `405` | Path exists but the method is not allowed (response includes `Allow`) |
| `413` | Request body larger than 1 MiB                                    |
| `500` | Unexpected server or database error                               |
| `503` | `/health` only: database unreachable                              |

## Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-306-40615-7"}'

# List, filtered by author
curl 'localhost:8080/books?author=frank%20herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

Validation error example:

```json
{
  "error": "validation failed",
  "details": {
    "title": "title is required",
    "author": "author is required"
  }
}
```

## Project layout

```
main.go                    entry point: config, server lifecycle, graceful shutdown
internal/book/             Book type and validation rules
internal/store/            SQLite persistence (schema, queries)
internal/api/              HTTP routing, handlers, and JSON responses
```
