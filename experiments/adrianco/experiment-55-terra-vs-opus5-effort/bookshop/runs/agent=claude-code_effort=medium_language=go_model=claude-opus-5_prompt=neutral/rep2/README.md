# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library's `net/http` router and backed by SQLite.

- **Language/framework:** Go 1.22+, standard library only (`net/http`, `database/sql`)
- **Database:** SQLite via [`modernc.org/sqlite`](https://modernc.org/sqlite), a
  pure-Go driver — no cgo and no system SQLite installation required

## Setup

```sh
go mod download
go build -o bookapi .
```

## Run

```sh
./bookapi
# or, without building a binary first:
go run .
```

The server listens on `:8080` and stores data in `./books.db`, creating the file
and schema on first start. Both are configurable:

| Variable  | Default    | Description                                   |
| --------- | ---------- | --------------------------------------------- |
| `ADDR`    | `:8080`    | Listen address                                |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral)   |

```sh
ADDR=:3000 DB_PATH=/var/lib/books/books.db ./bookapi
```

`SIGINT`/`SIGTERM` trigger a graceful shutdown that lets in-flight requests
finish (10s timeout).

## Tests

```sh
go test ./...          # all unit + integration tests
go test -race -v ./... # with the race detector
```

The suite covers the storage layer directly and every endpoint through the
router via `httptest`, using an in-memory database per test so runs are
isolated and need no fixtures. `TestStorePersistsAcrossReopen` uses a real
temporary file to prove rows survive a restart.

## API

All request and response bodies are JSON. Requests with a body must send
`Content-Type: application/json`.

### `GET /health`

Liveness plus a database round-trip. Returns `200` when healthy, `503` when the
database is unreachable.

```json
{ "status": "ok", "database": "ok" }
```

### `POST /books`

Creates a book. Responds `201` with the stored book and a `Location` header.

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

```json
{ "id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593" }
```

### `GET /books`

Lists books ordered by ID. `?author=` filters by exact author, matched
case-insensitively.

```sh
curl 'localhost:8080/books?author=frank%20herbert'
```

```json
{ "books": [ { "id": 1, "title": "Dune", "...": "..." } ], "count": 1 }
```

### `GET /books/{id}`

Returns one book, or `404` if the ID is unknown.

### `PUT /books/{id}`

Replaces a book. This is a **full replacement**, not a patch: fields omitted
from the payload are reset, so `year` and `isbn` are cleared unless resent.
`title` and `author` are required, exactly as on create.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969}'
```

### `DELETE /books/{id}`

Deletes a book. Responds `204` with no body, or `404` if the ID is unknown.

## Validation rules

| Field    | Rule                                                                 |
| -------- | -------------------------------------------------------------------- |
| `title`  | **Required.** Trimmed; must be non-empty and at most 500 characters.  |
| `author` | **Required.** Trimmed; must be non-empty and at most 500 characters.  |
| `year`   | Optional. `0` or omitted means unknown; otherwise 1 … current year+5. |
| `isbn`   | Optional. Hyphens/spaces stripped; must then be 10 digits (last may be `X`) or 13 digits. Must be unique across the collection. |

Unknown JSON fields are rejected, so a typo like `"tilte"` fails loudly instead
of silently creating an untitled book. Bodies are capped at 1 MiB.

## Status codes

| Code | Meaning                                                              |
| ---- | -------------------------------------------------------------------- |
| 200  | Successful `GET`, `PUT`                                              |
| 201  | Book created                                                         |
| 204  | Book deleted                                                         |
| 400  | Validation failure, malformed JSON, or a non-numeric `{id}`           |
| 404  | No book with that ID (or unknown route)                              |
| 405  | Method not supported for that path                                   |
| 409  | Another book already uses that ISBN                                  |
| 415  | `Content-Type` was not `application/json`                            |
| 503  | Database unreachable (`/health` only)                                |

Errors use a consistent envelope, with per-field detail for validation
failures:

```json
{ "error": "validation failed", "fields": { "title": "is required" } }
```

## Layout

| File             | Contents                                                    |
| ---------------- | ----------------------------------------------------------- |
| `main.go`        | Configuration, server startup, graceful shutdown            |
| `server.go`      | Routes, request decoding, JSON responses, error → status map |
| `store.go`       | SQLite schema and CRUD queries                              |
| `book.go`        | `Book` model and input validation                           |
| `server_test.go` | HTTP-level integration tests                                |
| `store_test.go`  | Storage and validation unit tests                           |

## Design notes

- **Input pointers.** `BookInput` uses pointer fields so an absent key is
  distinguishable from an empty value, which keeps `DisallowUnknownFields` and
  the required-field checks unambiguous.
- **`NULL` vs empty ISBN.** An omitted ISBN is stored as `NULL`, not `''`.
  SQLite's unique index ignores `NULL`s, so uniqueness is enforced only for
  books that actually have an ISBN.
- **Single connection.** The pool is capped at one connection. SQLite allows one
  writer at a time, and this also makes `:memory:` usable in tests, where each
  connection would otherwise get its own private database.
- **No-op updates.** A `PUT` writing identical values affects zero rows, which
  would look like a missing record; `Update` re-checks existence before
  reporting `404`.
