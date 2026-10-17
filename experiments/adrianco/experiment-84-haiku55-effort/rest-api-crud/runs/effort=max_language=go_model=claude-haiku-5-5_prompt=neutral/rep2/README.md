# Book Collection API

A REST service for managing a book collection. It is written in Go with the
standard library's `net/http` and stores data in SQLite.

## Requirements

- Go 1.26 or newer
- No C compiler is needed. The SQLite driver, `modernc.org/sqlite`, is pure Go.

## Setup

```sh
go mod download
```

## Run

Run it directly:

```sh
go run . -addr :8080 -db books.db
```

Or build a binary and run that:

```sh
go build -o bookapi .
./bookapi -addr :8080 -db books.db
```

| Flag   | Default    | Purpose                                                      |
|--------|------------|--------------------------------------------------------------|
| `-addr`| `:8080`    | Address to listen on                                         |
| `-db`  | `books.db` | SQLite database file. It and its schema are created on first start. |

The server logs each request to stderr. On `Ctrl+C` (SIGINT) or SIGTERM it stops
accepting connections, lets in-flight requests finish for up to 10 seconds, and
exits.

## Test

```sh
go test ./...
```

Add `-race` to check for data races. The race detector needs cgo, so run it with
`CGO_ENABLED=1` and a C compiler installed.

The tests cover validation rules, the SQLite store (including persistence across
a reopen and concurrent writes), every endpoint's status codes and bodies, and a
full create-read-update-delete cycle over a live HTTP server.

## API

All request and response bodies are JSON.

A book looks like this:

```json
{
  "id": 1,
  "title": "The Left Hand of Darkness",
  "author": "Ursula K. Le Guin",
  "year": 1969,
  "isbn": "978-0441478125"
}
```

`year` and `isbn` are `null` when they have not been set.

| Method   | Path           | Success                              | Other responses                                        |
|----------|----------------|--------------------------------------|--------------------------------------------------------|
| `POST`   | `/books`       | `201` with the created book and a `Location` header | `400` invalid body, `413` body too large |
| `GET`    | `/books`       | `200` with an array of books         | Optional `?author=` filter (see below)                 |
| `GET`    | `/books/{id}`  | `200` with the book                  | `400` id is not an integer, `404` no such book         |
| `PUT`    | `/books/{id}`  | `200` with the updated book          | `400` invalid body, `404` no such book, `413` body too large |
| `DELETE` | `/books/{id}`  | `204` with no body                   | `400` id is not an integer, `404` no such book         |
| `GET`    | `/health`      | `200` `{"status":"ok"}`              | `503` `{"status":"unavailable"}` if the database cannot be reached |

### Request fields

| Field    | Type    | Required | Rules                                                              |
|----------|---------|----------|--------------------------------------------------------------------|
| `title`  | string  | yes      | Non-blank after trimming whitespace; at most 500 characters        |
| `author` | string  | yes      | Non-blank after trimming whitespace; at most 200 characters        |
| `year`   | integer | no       | Between 1 and next calendar year, so forthcoming titles are allowed |
| `isbn`   | string  | no       | An ISBN-10 or ISBN-13. Hyphens and spaces are allowed, and an ISBN-10 may end in `X`. The check digit is not verified. A blank value is treated as not set. |

Unknown fields are ignored. An `id` sent in the body is ignored, because the
server assigns IDs.

`PUT` replaces the whole book. `title` and `author` are required, and omitting
`year` or `isbn` clears them. To change only one field, send the complete book
with that field changed.

### Filtering the list

`GET /books?author=<text>` returns the books whose author contains `<text>`,
ignoring case. For example, `?author=herbert` matches "Frank Herbert". Leading and
trailing spaces are trimmed, and a blank value is the same as no filter. Case
folding applies to ASCII letters only, which is how SQLite's `LIKE` works. The
results are in ID order.

### Errors

Every error response is JSON with an `error` message. Validation failures also
include a `fields` object that maps each bad field to its problem:

```json
{"error": "validation failed", "fields": {"title": "is required", "year": "must be between 1 and 2027"}}
```

Requests for an unknown path return `404`, and requests with an unsupported
method return `405` with an `Allow` header.

## Examples

```sh
# Create a book
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}'

# List all books, or only those by an author
curl http://localhost:8080/books
curl 'http://localhost:8080/books?author=herbert'

# Get, replace, and delete book 1
curl http://localhost:8080/books/1
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Layout

All Go source is in the repository root, as a single `package main`:

| File           | Contents                                                              |
|----------------|-----------------------------------------------------------------------|
| `main.go`      | Command-line flags, startup, and graceful shutdown                    |
| `book.go`      | The `Book` type, input normalization, and validation rules            |
| `store.go`     | SQLite persistence                                                    |
| `server.go`    | Routing, handlers, JSON and error responses, and request logging      |
| `*_test.go`    | Unit, store, HTTP, and end-to-end tests                               |

## Design notes

- **Routing** uses the standard library's `net/http` mux. Paths are matched by
  the mux, and each handler dispatches on method. This keeps 404 and 405 responses
  as JSON, as the rest of the API does.
- **Storage** uses SQLite in WAL mode. The connection pool holds a single
  connection, because SQLite allows only one writer at a time. WAL mode creates
  `books.db-wal` and `books.db-shm` next to the database file. Don't delete them
  by hand. After an unexpected stop, the `-wal` file can hold committed writes
  that are not yet in `books.db`; SQLite applies them the next time the database
  is opened.
- **Limits:** bodies are capped at 1 MiB. Server timeouts are set so that slow
  clients cannot hold connections open indefinitely.

## Not included

- Authentication and authorization
- Pagination. `GET /books` returns the entire collection.
- Checksum validation of ISBNs
- Duplicate detection. Two books may have the same ISBN, which allows for
  multiple copies.
