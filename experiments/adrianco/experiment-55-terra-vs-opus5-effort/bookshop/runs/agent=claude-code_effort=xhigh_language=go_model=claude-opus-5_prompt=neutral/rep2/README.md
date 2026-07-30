# bookapi

A REST API for managing a book collection, written in Go with SQLite storage.

The HTTP layer is Go's standard-library `net/http` (using the method-aware
routing patterns added in Go 1.22), and persistence is
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) — a pure-Go
SQLite implementation, so the service builds and runs without cgo or a C
toolchain.

## Requirements

- Go 1.25 or newer
- No other dependencies; the database file is created on first run

## Run it

```sh
go run .                       # listens on :8080, stores data in ./books.db
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi -addr 127.0.0.1:8080 -db /var/lib/bookapi/books.db
```

Check that it is up:

```sh
curl -s localhost:8080/health
# {"database":"ok","status":"ok"}
```

### Configuration

| Flag | Environment variable | Default | Description |
| --- | --- | --- | --- |
| `-addr` | `BOOKAPI_ADDR`, or `PORT` (as `:$PORT`) | `:8080` | TCP address to listen on |
| `-db` | `BOOKAPI_DB` | `books.db` | SQLite database file; `:memory:` for an ephemeral database |
| `-log-format` | `BOOKAPI_LOG_FORMAT` | `text` | `text` or `json` structured logging to stderr |

Flags take precedence over environment variables. `SIGINT`/`SIGTERM` triggers
a graceful shutdown: the listener closes and in-flight requests get up to 10
seconds to finish.

## Tests

```sh
go test ./...              # unit + integration tests
go test -race -cover ./... # with the race detector and coverage (~89%)
```

The suite covers three layers:

- `book_test.go` — validation and ISBN normalisation rules.
- `store_test.go` — the SQLite layer against a real database file, including
  concurrent writers, `NULL` handling for optional fields, and the unique-ISBN
  constraint.
- `api_test.go` — the endpoints over a real HTTP server (`httptest`), covering
  the full lifecycle, every error status, and behaviour when the database is
  unavailable.
- `main_test.go` — configuration precedence and graceful shutdown draining an
  in-flight request.

## API

All responses are JSON. Every request body must be a JSON object with
`Content-Type: application/json`.

| Method | Path | Success | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | `200` | Service and database status |
| `POST` | `/books` | `201` | Create a book (`Location` header points at it) |
| `GET` | `/books` | `200` | List all books, oldest first; `?author=` filters |
| `GET` | `/books/{id}` | `200` | Fetch one book |
| `PUT` | `/books/{id}` | `200` | Replace a book |
| `DELETE` | `/books/{id}` | `204` | Delete a book |

### The book resource

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan A. A. Donovan",
  "year": 2015,
  "isbn": "9780134190440",
  "created_at": "2026-07-30T05:24:41.650285Z",
  "updated_at": "2026-07-30T05:24:41.650285Z"
}
```

`id`, `created_at` and `updated_at` are managed by the server. They are
accepted and ignored in request bodies, so a client can `GET` a book, edit a
field and `PUT` the whole document back.

`year` is `null` and `isbn` is `""` when not recorded. (A missing year is
`null` rather than `0` because `0` would look like real data; an empty string
is unambiguous for an ISBN.)

### Validation

| Field | Rule |
| --- | --- |
| `title` | Required, non-blank after trimming, at most 512 characters |
| `author` | Required, non-blank after trimming, at most 256 characters |
| `year` | Optional; between 1000 and next year |
| `isbn` | Optional; a valid ISBN-10 or ISBN-13 (check digit verified), unique across the collection |

Hyphens and spaces are stripped from an ISBN before storing, so
`978-0-13-419044-0` and `9780134190440` are the same book and cannot both be
added. `title` and `author` are stored with surrounding whitespace trimmed.

### `POST /books`

```sh
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0-13-419044-0"}'
```

```http
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
Location: /books/1
```

### `GET /books`

Returns a JSON array (`[]` when empty), ordered by id.

```sh
curl -s localhost:8080/books
curl -s 'localhost:8080/books?author=frank%20herbert'
```

The `author` filter matches the whole author field, case-insensitively; an
empty `?author=` is the same as no filter. Other query parameters are ignored.

### `PUT /books/{id}`

`PUT` replaces the resource, so it takes the same body as `POST` — `title` and
`author` are required, and any optional field left out is **cleared**. `id` and
`created_at` are preserved; `updated_at` advances.

```sh
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan, Brian W. Kernighan","year":2015}'
```

### Errors

Errors share one envelope, with a stable `code` for programmatic handling and
per-field detail for validation failures:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "the request body failed validation",
    "fields": [{ "field": "title", "message": "is required" }]
  }
}
```

| Status | `code` | Cause |
| --- | --- | --- |
| `400` | `validation_failed` | A field broke one of the rules above |
| `400` | `invalid_json` | Body empty, malformed, not an object, or carrying an unknown field |
| `400` | `invalid_id` | `{id}` is not a positive integer |
| `404` | `not_found` | No book with that id, or no such route |
| `405` | `method_not_allowed` | Wrong method for a known path (with an `Allow` header) |
| `409` | `isbn_taken` | Another book already has that ISBN |
| `413` | `request_too_large` | Body over 1 MiB |
| `415` | `unsupported_media_type` | `Content-Type` is not `application/json` |
| `500` | `internal_error` | Unexpected server-side failure (details go to the log, not the response) |
| `503` | — | `GET /health` only: the database is unreachable |

Unknown fields in a request body are rejected rather than ignored, so a typo
like `{"titel": "..."}` fails loudly instead of silently discarding data.

## Layout

| File | Contents |
| --- | --- |
| `main.go` | Configuration, startup, graceful shutdown |
| `api.go` | Routing, handlers, request decoding, JSON responses, middleware |
| `book.go` | The `Book` model, validation, ISBN normalisation |
| `store.go` | SQLite schema and queries |

### Storage notes

The schema is applied at startup and is idempotent, so pointing the service at
an existing database file is safe:

```sql
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER,
	isbn       TEXT    UNIQUE,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS books_author_nocase ON books (author COLLATE NOCASE);
```

- Optional fields are stored as `NULL`. Because SQLite's `UNIQUE` index ignores
  `NULL`s, any number of books may have no ISBN while the ones that do stay
  unique.
- File-backed databases run in WAL mode with a busy timeout, so readers do not
  block on a writer and concurrent writers queue instead of failing.
- Timestamps are stored as nanosecond-precision UTC text, which sorts
  lexicographically and keeps `updated_at` strictly increasing.
