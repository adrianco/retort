# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` router and SQLite storage via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver (no cgo
or system SQLite required).

## Requirements

- Go 1.22+ (developed with Go 1.26)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi
```

Configuration is via environment variables:

| Variable  | Default     | Description                    |
|-----------|-------------|--------------------------------|
| `ADDR`    | `:8080`     | Address the HTTP server binds  |
| `DB_PATH` | `books.db`  | Path to the SQLite database    |

Example:

```sh
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

## Test

```sh
go test ./...
```

## Data model

| Field    | Type    | Rules                                                        |
|----------|---------|--------------------------------------------------------------|
| `id`     | integer | Assigned by the server (read-only)                           |
| `title`  | string  | **Required**, whitespace is trimmed                          |
| `author` | string  | **Required**, whitespace is trimmed                          |
| `year`   | integer | Optional, must not be negative (defaults to `0`)             |
| `isbn`   | string  | Optional; if present, must be ISBN-10 or ISBN-13 (hyphens allowed) |

## Endpoints

| Method   | Path          | Description                                  | Success     |
|----------|---------------|----------------------------------------------|-------------|
| `GET`    | `/health`     | Health check                                 | `200`       |
| `POST`   | `/books`      | Create a book                                | `201`       |
| `GET`    | `/books`      | List books; optional `?author=` filter       | `200`       |
| `GET`    | `/books/{id}` | Get a book by ID                             | `200`       |
| `PUT`    | `/books/{id}` | Replace a book (full update)                 | `200`       |
| `DELETE` | `/books/{id}` | Delete a book                                | `204`       |

The `?author=` filter is an exact match that ignores case.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190570"}'

# List, filtered by author
curl 'localhost:8080/books?author=alan%20donovan'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2016}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Errors

Errors are returned as JSON:

```json
{"error": "book not found"}
```

| Status | When                                                              |
|--------|-------------------------------------------------------------------|
| `400`  | Malformed JSON body, or `{id}` is not a positive integer          |
| `404`  | No book with the given ID                                         |
| `405`  | Method not allowed on the path                                    |
| `422`  | Validation failed; the response includes a `fields` map, e.g. `{"error":"validation failed","fields":{"title":"is required"}}` |
| `500`  | Unexpected server or database error                               |

Request bodies are limited to 1 MiB.
