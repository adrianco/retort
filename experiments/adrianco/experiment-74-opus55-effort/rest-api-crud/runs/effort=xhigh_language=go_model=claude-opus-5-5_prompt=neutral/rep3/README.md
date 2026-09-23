# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library's `net/http` router and an embedded SQLite database
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
driver, so no C compiler or cgo is needed).

## Requirements

- Go 1.25 or newer

## Setup and run

```sh
go mod download      # fetch dependencies
go run .             # listens on :8080, stores data in ./books.db
```

Or build a binary:

```sh
go build -o bookapi .
./bookapi -addr :9000 -db /var/lib/bookapi/books.db
```

| Flag    | Env var   | Default    | Meaning                                                          |
|---------|-----------|------------|------------------------------------------------------------------|
| `-addr` | `ADDR`    | `:8080`    | Listen address                                                   |
| `-db`   | `DB_PATH` | `books.db` | SQLite file (created if missing), or `:memory:` for a throwaway DB |

Flags take precedence over environment variables. The schema is created
automatically on startup. The server shuts down gracefully on `SIGINT` or `SIGTERM`.

## Running the tests

```sh
go test ./...
go test -race ./...  # with the race detector
```

The tests cover validation and ISBN checksums (`book_test.go`), the SQLite
store (`store_test.go`) and every HTTP endpoint (`api_test.go`), including a
test that starts the real server on a random port and sends it concurrent
requests.

## API

All responses are JSON (`Content-Type: application/json`) except the empty
`204` reply to `DELETE`.

### Book resource

```json
{
  "id": 1,
  "title": "The Hobbit",
  "author": "J.R.R. Tolkien",
  "year": 1937,
  "isbn": "9780306406157",
  "created_at": "2026-09-23T00:13:44.615855Z",
  "updated_at": "2026-09-23T00:13:44.615855Z"
}
```

`year` and `isbn` are optional and are `null` when not set.

### Endpoints

| Method   | Path          | Success               | Errors               |
|----------|---------------|-----------------------|----------------------|
| `GET`    | `/health`     | 200                   | 503 if the DB is unreachable |
| `POST`   | `/books`      | 201 + `Location` header | 400, 409, 413      |
| `GET`    | `/books`      | 200 (array, `[]` if empty) | —               |
| `GET`    | `/books/{id}` | 200                   | 400, 404             |
| `PUT`    | `/books/{id}` | 200                   | 400, 404, 409, 413   |
| `DELETE` | `/books/{id}` | 204                   | 400, 404             |

- **`GET /books?author=…`** returns only books whose author *contains* the
  given text, ignoring case (`?author=tolkien` matches `J.R.R. Tolkien`).
  `%` and `_` are matched literally. Results are ordered by `id`.
- **`PUT`** replaces the whole book. `title` and `author` are required, and
  leaving out `year` or `isbn` clears that field.
- IDs are never reused after a delete.

### Validation rules

| Field    | Rule |
|----------|------|
| `title`  | Required; surrounding whitespace is trimmed; at most 500 characters |
| `author` | Required; surrounding whitespace is trimmed; at most 300 characters |
| `year`   | Optional integer from 1 to next year (next year is allowed so forthcoming books can be added) |
| `isbn`   | Optional; must be a valid ISBN-10 or ISBN-13 with a correct check digit. Hyphens and spaces are allowed on input, and the value is stored without them (for example, `978-0-306-40615-7` is stored as `9780306406157`). Each ISBN can belong to only one book; a duplicate returns `409 Conflict`. |

The request body must be a single JSON object of at most 1 MiB. Unknown fields
are ignored, so you can send back a book object from a `GET` response as a
`PUT` body.

### Errors

Every error has the same shape:

```json
{"error": "book not found"}
```

A validation failure also lists the fields that failed:

```json
{
  "error": "validation failed",
  "fields": {"title": "is required", "isbn": "must be a valid ISBN-10 or ISBN-13"}
}
```

Unknown routes return `404`. A route used with the wrong method returns `405`
with an `Allow` header. Both use the same JSON error shape.

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-306-40615-7"}'

# List all, or filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=tolkien'

# Get one
curl localhost:8080/books/1

# Update (full replacement)
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Hobbit, or There and Back Again","author":"J.R.R. Tolkien","year":1937}'

# Delete
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Project layout

| File          | Contents |
|---------------|----------|
| `main.go`     | Flag and environment configuration, HTTP server lifecycle, graceful shutdown |
| `handlers.go` | Routes, request decoding, JSON responses, logging and panic-recovery middleware |
| `store.go`    | SQLite schema and data access (`Create`, `List`, `Get`, `Update`, `Delete`) |
| `book.go`     | `Book` model, input normalisation and validation, ISBN checksums |
| `*_test.go`   | Unit and integration tests |

## Notes

- For a database file, SQLite runs in WAL mode with a 5-second busy timeout,
  so concurrent reads and writes don't fail with `SQLITE_BUSY`.
- The author filter's case-insensitivity covers ASCII letters only, which is
  SQLite's built-in `LIKE` behaviour.
- The ISBN-10 and ISBN-13 forms of the same book are treated as different ISBNs.
