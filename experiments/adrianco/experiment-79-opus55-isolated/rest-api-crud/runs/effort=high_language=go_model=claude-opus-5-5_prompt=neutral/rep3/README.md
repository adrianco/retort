# Books API

A small REST service for managing a book collection, written in Go with the
standard library's `net/http` router and backed by SQLite.

## Requirements

- Go 1.26 or newer

SQLite is provided by [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
a pure-Go driver, so no C compiler or system SQLite library is needed.

## Setup and run

```sh
go mod download      # fetch dependencies
go run .             # start the server on :8080, storing data in ./books.db
```

Or build a binary:

```sh
go build -o books .
./books -addr :9000 -db /var/lib/books/books.db
```

| Flag    | Environment variable | Default    | Description                       |
| ------- | -------------------- | ---------- | --------------------------------- |
| `-addr` | `ADDR`               | `:8080`    | Address to listen on              |
| `-db`   | `DB_PATH`            | `books.db` | Path to the SQLite database file  |

A flag takes precedence over its environment variable. The database file and
its schema are created on first start. The server shuts down gracefully on
`SIGINT`/`SIGTERM`.

## Tests

```sh
go test ./...
```

The tests run the full HTTP stack against temporary SQLite databases; nothing
needs to be running beforehand.

## API

All request and response bodies are JSON.

| Method   | Path          | Description                          | Success          |
| -------- | ------------- | ------------------------------------ | ---------------- |
| `GET`    | `/health`     | Health check (also pings the DB)     | `200 OK`         |
| `POST`   | `/books`      | Create a book                        | `201 Created`    |
| `GET`    | `/books`      | List books, optionally by `?author=` | `200 OK`         |
| `GET`    | `/books/{id}` | Get one book                         | `200 OK`         |
| `PUT`    | `/books/{id}` | Replace a book                       | `200 OK`         |
| `DELETE` | `/books/{id}` | Delete a book                        | `204 No Content` |

### Book

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "9780441013593"
}
```

| Field    | Type    | Rules                                                     |
| -------- | ------- | --------------------------------------------------------- |
| `id`     | integer | Assigned by the server; ignored if sent in a request body |
| `title`  | string  | Required, at most 500 characters                          |
| `author` | string  | Required, at most 200 characters                          |
| `year`   | integer | Optional, 0–9999; `0` means "not set"                     |
| `isbn`   | string  | Optional, at most 32 characters; format is not checked    |

Leading and trailing whitespace is trimmed from string fields, so a title or
author made only of whitespace counts as missing.

### Behaviour worth knowing

- `PUT` is a full replacement: optional fields left out of the body are reset
  to their empty values rather than kept.
- `GET /books?author=` matches the whole author name, ignoring ASCII case
  (`?author=frank herbert` matches `Frank Herbert`; `?author=Frank` does not).
  An empty `author` parameter is ignored.
- `GET /books` returns books ordered by ID, and `[]` when there are none.
- IDs are never reused after a book is deleted.
- Request bodies are limited to 1 MiB.

### Errors

Errors are JSON objects with an `error` message. Validation failures also list
the offending fields:

```json
{
  "error": "validation failed",
  "fields": {
    "author": "author is required",
    "title": "title is required"
  }
}
```

| Status | Meaning                                                           |
| ------ | ----------------------------------------------------------------- |
| `400`  | Malformed JSON, wrong field type, failed validation, or a bad ID  |
| `404`  | No book with that ID, or an unknown path                          |
| `405`  | Method not supported on that path (see the `Allow` header)        |
| `413`  | Request body larger than 1 MiB                                    |
| `500`  | Unexpected server error                                           |
| `503`  | `/health` only: the database is unreachable                       |

### Examples

```sh
# Create
curl -i -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'

# List, optionally filtered by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Frank%20Herbert'

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965}'
curl -i -X DELETE localhost:8080/books/1

# Health
curl localhost:8080/health
```

## Layout

| File               | Contents                                            |
| ------------------ | --------------------------------------------------- |
| `main.go`          | Flags, server start-up and graceful shutdown        |
| `handlers.go`      | Routing, request decoding, validation, responses    |
| `store.go`         | SQLite schema and queries                           |
| `handlers_test.go` | End-to-end tests of the HTTP API                    |
| `store_test.go`    | Tests of the persistence layer                      |
