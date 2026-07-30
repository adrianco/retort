# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library's `net/http` router and a SQLite database.

## Requirements

- Go 1.25 or newer (required by the SQLite driver)

No C toolchain is needed: persistence uses [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go SQLite implementation, so `CGO_ENABLED=0` builds work fine.

## Setup and run

```sh
go mod download
go run .
```

The server listens on `:8080` and creates `books.db` in the working directory on
first start. Both are configurable:

| Variable  | Default    | Description                                     |
|-----------|------------|-------------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                                  |
| `DB_PATH` | `books.db` | SQLite file path; `:memory:` for a throwaway DB |

```sh
ADDR=127.0.0.1:9000 DB_PATH=/var/lib/books/books.db go run .
```

To build a binary instead:

```sh
go build -o bookapi .
./bookapi
```

The server shuts down gracefully on `SIGINT`/`SIGTERM`, giving in-flight
requests up to 10 seconds to finish.

## Tests

```sh
go test ./...          # all tests
go test -race ./...    # with the race detector
go test -v ./...       # per-case output
```

The suite covers the HTTP surface end to end (a real SQLite store on an
in-memory database) plus unit tests for validation and the storage layer:

- `api_test.go` — request/response behaviour for every endpoint: creation and
  read-back, the author filter (including case-insensitivity and the empty
  result), validation failures, updates, deletes, duplicate ISBN conflicts, and
  routing errors.
- `book_test.go` — ISBN check-digit validation, field validation rules, input
  normalization, store-level `ErrNotFound`/`ErrDuplicateISBN`, and a
  close-and-reopen test proving data is actually persisted to disk.

## API

All responses are JSON. Request bodies must be `application/json`.

### `GET /health`

Returns `200` when the database responds to a ping, `503` otherwise.

```json
{ "status": "ok", "database": "up" }
```

### `POST /books`

Creates a book. `title` and `author` are required.

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

`201 Created`, with a `Location` header pointing at the new resource:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593",
  "created_at": "2026-07-30T05:05:28.309794Z",
  "updated_at": "2026-07-30T05:05:28.309794Z"
}
```

### `GET /books`

Lists books ordered by ID. `?author=` filters on an exact, case-insensitive
author match.

```sh
curl 'localhost:8080/books?author=frank%20herbert'
```

```json
{ "books": [ { "id": 1, "title": "Dune", "...": "..." } ], "count": 1 }
```

`books` is always an array — never `null` — when there are no matches.

### `GET /books/{id}`

Returns a single book, or `404` if the ID is unknown.

### `PUT /books/{id}`

Replaces every mutable field. Because it is a full replacement rather than a
patch, omitted optional fields (`year`, `isbn`) are cleared, and `title` and
`author` must still be supplied.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune (Deluxe Edition)","author":"Frank Herbert","year":1965}'
```

`created_at` is preserved; `updated_at` advances.

### `DELETE /books/{id}`

`204 No Content` with an empty body. Deleting an already-deleted book is a
`404` rather than a silent success.

## Validation rules

| Field    | Rule                                                                      |
|----------|---------------------------------------------------------------------------|
| `title`  | Required, non-blank after trimming, at most 500 characters                 |
| `author` | Required, non-blank after trimming, at most 500 characters                 |
| `year`   | Optional; `0` means unknown, otherwise between 1400 and next year          |
| `isbn`   | Optional; must be a valid ISBN-10 or ISBN-13 including the check digit     |

`title` and `author` are trimmed of surrounding whitespace. ISBNs are
normalized by stripping hyphens and spaces and upper-casing an `X` check digit,
so `0-306-40615-2` and `0306406152` are stored — and compared — identically.

Non-empty ISBNs are unique across the collection; a collision returns `409`.
Blank ISBNs are exempt, so any number of books may omit one.

## Status codes

| Code | Meaning                                                            |
|------|--------------------------------------------------------------------|
| 200  | Successful read or update                                          |
| 201  | Book created                                                       |
| 204  | Book deleted                                                       |
| 400  | Malformed JSON, unknown field, or a non-numeric ID                  |
| 404  | No such book or route                                              |
| 405  | Method not supported for that route                                |
| 409  | ISBN already belongs to another book                               |
| 413  | Request body over 1 MiB                                            |
| 415  | `Content-Type` is not `application/json`                           |
| 422  | Body parsed, but field validation failed                           |
| 500  | Unexpected server-side failure                                     |
| 503  | Health check failed — the database is unreachable                  |

Errors share one shape. Field-level problems appear under `fields`:

```json
{ "error": "validation failed", "fields": { "title": "title is required" } }
```

```json
{ "error": "book not found" }
```

Unknown JSON fields are rejected rather than ignored, so typos like
`{"titel": "..."}` surface as a `400` instead of silently creating a book with
an empty title.

## Layout

| File           | Contents                                                       |
|----------------|----------------------------------------------------------------|
| `main.go`      | Configuration, server startup, graceful shutdown                |
| `api.go`       | Routing, request decoding, JSON responses, error mapping        |
| `store.go`     | SQLite schema, migration, and CRUD queries                      |
| `book.go`      | The `Book` model, input normalization, and validation rules     |
| `api_test.go`  | End-to-end HTTP tests                                           |
| `book_test.go` | Validation and storage-layer unit tests                         |

## Design notes

- **Routing** uses Go 1.22+ `net/http` method patterns (`GET /books/{id}`), so
  no third-party router is required. A response wrapper rewrites the router's
  plain-text 404/405 bodies into the same JSON error shape; a catch-all `/`
  route would have shadowed the mux's method-not-allowed handling.
- **Connections** are capped at one, which keeps writers from contending and
  guarantees an in-memory database is visible to every query. A busy timeout is
  set, and file-backed databases run in WAL mode.
- **Layering** keeps the store free of HTTP concerns: it returns sentinel errors
  (`ErrNotFound`, `ErrDuplicateISBN`) that the HTTP layer maps to status codes.
- **Robustness**: request bodies are capped at 1 MiB, the server sets read,
  write, and idle timeouts, and a recovery middleware converts a handler panic
  into a `500` rather than tearing down the process.
