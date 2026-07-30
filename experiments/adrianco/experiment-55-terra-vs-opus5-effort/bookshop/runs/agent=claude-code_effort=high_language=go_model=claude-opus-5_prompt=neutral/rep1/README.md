# bookapi

A small REST API for managing a book collection, written in Go with only the
standard library plus a pure-Go SQLite driver.

- **HTTP**: `net/http` and `http.ServeMux` (method + wildcard routing, Go 1.22+)
- **Storage**: SQLite via [`modernc.org/sqlite`](https://modernc.org/sqlite) —
  pure Go, so no CGO and no C toolchain required
- **Dependencies**: none beyond that driver

## Requirements

- Go 1.25 or newer (required by the SQLite driver; see `go.mod`)

## Setup and run

```sh
go mod download        # fetch the SQLite driver
go build -o bookapi .  # or: go run .
./bookapi
```

The server listens on `:8080` and stores data in `./books.db`, creating the
file and schema on first start.

| Flag    | Environment    | Default    | Description                                        |
| ------- | -------------- | ---------- | -------------------------------------------------- |
| `-addr` | `BOOKAPI_ADDR` | `:8080`    | TCP address to listen on                           |
| `-db`   | `BOOKAPI_DB`   | `books.db` | SQLite file; `:memory:` for an ephemeral database  |

```sh
./bookapi -addr 127.0.0.1:9000 -db /var/lib/bookapi/books.db
```

`SIGINT`/`SIGTERM` trigger a graceful shutdown (in-flight requests get up to
10 seconds to finish).

## Tests

```sh
go test ./...           # all tests
go test -race -v ./...  # verbose, with the race detector
go test -cover ./...    # with coverage
```

`store_test.go` covers the persistence layer (CRUD, `ErrNotFound` semantics,
case-insensitive filtering, survival across a restart, concurrent writes, and
input validation). `server_test.go` covers the HTTP surface end to end against
a real temporary SQLite database, including status codes, headers, validation
errors, and routing failures.

## API

All responses are JSON. Request bodies must be `application/json`; unknown
fields are rejected so that a typo such as `titel` fails loudly instead of
silently creating a book with no title.

### `GET /health`

`200` when the database responds, `503` otherwise.

```json
{ "status": "ok", "database": "ok" }
```

### `POST /books`

Creates a book. `title` and `author` are required; `year` and `isbn` are
optional. Returns `201` with the created book and a `Location` header.

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-01359-3"}'
```

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0-441-01359-3",
  "created_at": "2026-07-30T02:05:18.436809Z",
  "updated_at": "2026-07-30T02:05:18.436809Z"
}
```

### `GET /books`

Lists all books ordered by ID, as a JSON array (`[]` when empty). The optional
`?author=` query parameter filters by author using an exact,
**case-insensitive** match; a blank value is ignored.

```sh
curl 'localhost:8080/books?author=frank%20herbert'
```

### `GET /books/{id}`

Returns one book, or `404` if the ID does not exist.

### `PUT /books/{id}`

Full replacement of the client-owned fields — the same validation rules as
`POST` apply, and any optional field omitted from the body is **cleared**.
`id` and `created_at` are preserved; `updated_at` is refreshed. Returns `200`
with the stored book, or `404`.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
```

### `DELETE /books/{id}`

Returns `204` with an empty body, or `404` if the book is already gone.

## Validation

| Field    | Rule                                                                    |
| -------- | ----------------------------------------------------------------------- |
| `title`  | Required, non-blank, at most 500 characters                              |
| `author` | Required, non-blank, at most 200 characters                             |
| `year`   | Optional; when present must be between 1450 and 5 years from now         |
| `isbn`   | Optional; when present must be a 10- or 13-digit ISBN (hyphens/spaces OK) |

Leading and trailing whitespace is trimmed from all three text fields, so
`"   "` is not a valid title.

ISBN *shape* is checked but the check digit is not verified — real catalogues
contain plenty of legitimately mistyped ISBNs, and rejecting them is not this
service's job.

## Status codes

| Code  | When                                                                   |
| ----- | ---------------------------------------------------------------------- |
| `200` | Successful `GET` or `PUT`                                              |
| `201` | Book created                                                           |
| `204` | Book deleted                                                           |
| `400` | Validation failure, malformed/oversized JSON, or a non-numeric ID      |
| `404` | Unknown book ID or unknown endpoint                                    |
| `405` | Known path, unsupported method (with an `Allow` header)                |
| `415` | `Content-Type` is not `application/json`                               |
| `500` | Unexpected server or database error                                    |
| `503` | Health check could not reach the database                              |

Every error uses the same envelope, with a per-field `fields` object present
only for validation failures:

```json
{
  "error": "validation failed",
  "fields": { "title": "is required", "year": "must be between 1450 and 2031, or omitted" }
}
```

Internal failures are logged server-side and reported to the client as a plain
`{"error":"internal server error"}`, so database details never leak.

## Layout

| File             | Contents                                                     |
| ---------------- | ------------------------------------------------------------ |
| `main.go`        | Flags, startup, graceful shutdown                            |
| `server.go`      | Routing, request decoding, JSON responses, request logging   |
| `store.go`       | SQLite schema and CRUD queries                               |
| `book.go`        | `Book`/`BookInput` types and validation rules                |
| `server_test.go` | HTTP integration tests                                       |
| `store_test.go`  | Storage and validation unit tests                            |

## Notes on the SQLite setup

The connection pool is capped at one connection (`SetMaxOpenConns(1)`). SQLite
permits only one writer at a time; serialising access here trades a little read
concurrency for the guarantee that a burst of writes never surfaces
`SQLITE_BUSY` to a client. WAL journalling and a 5-second busy timeout are set
via DSN pragmas. For a read-heavy deployment, raising the limit and adding a
separate read pool would be the next step.
