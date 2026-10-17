# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library's `net/http` router and stored in SQLite. The SQLite driver is pure Go,
so no C compiler is needed.

## Requirements

- Go 1.26 or newer (the SQLite driver's `go.mod` requires it)

## Setup

```sh
go mod download
```

## Run

```sh
go run . -addr :8080 -db books.db
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi -addr :8080 -db books.db
```

| Flag    | Default   | Description                                      |
|---------|-----------|--------------------------------------------------|
| `-addr` | `:8080`   | HTTP listen address                              |
| `-db`   | `books.db`| Path to the SQLite file (created if it does not exist) |

The server shuts down gracefully on `Ctrl+C` or `SIGTERM`.

## Test

```sh
go test ./...
```

The suite includes unit tests for validation and ISBN checksums, store tests
against a real SQLite file, and HTTP integration tests that exercise every
endpoint through the full router and middleware.

## Data model

| Field    | Type            | Required | Rules                                                      |
|----------|-----------------|----------|------------------------------------------------------------|
| `id`     | integer         | (server) | Assigned on create. Read-only.                             |
| `title`  | string          | yes      | Non-blank after trimming, at most 500 characters           |
| `author` | string          | yes      | Non-blank after trimming, at most 500 characters           |
| `year`   | integer or null | no       | Between 1 and next calendar year                           |
| `isbn`   | string or null  | no       | Valid ISBN-10 or ISBN-13 (check digit verified)            |

Hyphens and spaces in an ISBN are removed, and a trailing `x` is upper-cased,
so `978-0-306-40615-7` is stored as `9780306406157`. A blank ISBN is treated as
absent.

## Endpoints

| Method   | Path          | Success               | Errors                              |
|----------|---------------|-----------------------|-------------------------------------|
| `POST`   | `/books`      | `201` + `Location`    | `400` validation, `413` body too large |
| `GET`    | `/books`      | `200` (array)         |                                     |
| `GET`    | `/books/{id}` | `200`                 | `400` bad id, `404` not found       |
| `PUT`    | `/books/{id}` | `200`                 | `400` validation or bad id, `404` not found |
| `DELETE` | `/books/{id}` | `204` (no body)       | `400` bad id, `404` not found       |
| `GET`    | `/health`     | `200` / `503`         |                                     |

Every response is JSON, including errors. Errors use the form
`{"error": "..."}`. Validation failures add a `fields` object that maps each
bad field to a message:

```json
{"error": "validation failed", "fields": {"title": "is required"}}
```

Unsupported methods return `405` with an `Allow` header. Unknown paths return
`404`.

### Filtering

`GET /books?author=<name>` returns only books whose author matches `<name>`.
The match is exact but case-insensitive, so `ursula k. le guin` matches
`Ursula K. Le Guin`. An empty `author=` parameter is ignored. Results are
ordered by `id`.

### PUT semantics

`PUT` replaces the whole record. Send every field you want to keep. Omitting
`year` or `isbn` clears them.

## Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"978-0-441-47812-5"}'

# List, filtered by author
curl 'localhost:8080/books?author=Ursula%20K.%20Le%20Guin'

# Get one
curl localhost:8080/books/1

# Update (full replacement)
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

| File           | Contents                                                |
|----------------|---------------------------------------------------------|
| `main.go`      | Flags, startup, and graceful shutdown                   |
| `server.go`    | Routes, JSON helpers, logging and panic-recovery middleware |
| `handlers.go`  | HTTP handlers and request decoding                      |
| `book.go`      | Book types, validation, and ISBN checks                 |
| `store.go`     | SQLite persistence                                      |
| `*_test.go`    | Unit, store, and HTTP integration tests                 |

## Notes

- ISBNs are not unique. A collection may hold several copies of one edition.
- The list endpoint has no pagination. That fits a personal collection, but
  large collections would need `limit` and `offset` parameters.
