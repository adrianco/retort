# Book Collection API

A JSON REST API for managing a book collection, written in Go using only the
standard library's HTTP router and an embedded SQLite database.

## Requirements

- Go 1.26.0 or newer
- No C toolchain needed: the SQLite driver ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)) is pure Go.

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

| Flag    | Default    | Description                                        |
|---------|------------|----------------------------------------------------|
| `-addr` | `:8080`    | Address to listen on                               |
| `-db`   | `books.db` | SQLite database file; created with the schema if missing |

The server shuts down gracefully on `SIGINT` or `SIGTERM`, letting in-flight
requests finish.

## Test

```sh
go test ./...
```

The suite covers:

- `internal/book`: input normalization, field validation, and ISBN-10/13 checksums (unit tests).
- `internal/store`: CRUD, author filtering, and persistence across reopening the database file (against a real SQLite file in a temp directory).
- `internal/server`: end-to-end HTTP tests of every endpoint, status code, and error shape.

## API

All requests and responses use JSON. Errors have the form:

```json
{"error": "book not found"}
```

Validation failures add a `details` object keyed by field name:

```json
{"error": "validation failed", "details": {"title": "is required"}}
```

### Book fields

| Field    | Type            | Required | Rules                                                                 |
|----------|-----------------|----------|-----------------------------------------------------------------------|
| `id`     | integer         | —        | Assigned by the server; read-only                                     |
| `title`  | string          | yes      | Non-blank after trimming; at most 500 characters                      |
| `author` | string          | yes      | Non-blank after trimming; at most 200 characters                      |
| `year`   | integer or null | no       | Between -3000 and next year                                           |
| `isbn`   | string or null  | no       | Valid ISBN-10 or ISBN-13 (checksum verified); hyphens and spaces are removed before storing |

### Endpoints

| Method   | Path          | Success                | Other statuses                                   |
|----------|---------------|------------------------|--------------------------------------------------|
| `POST`   | `/books`      | `201` + `Location` header and the book | `400` validation or malformed body   |
| `GET`    | `/books`      | `200` with an array (`?author=` optional) | —                                 |
| `GET`    | `/books/{id}` | `200` with the book    | `400` non-integer id, `404` not found            |
| `PUT`    | `/books/{id}` | `200` with the updated book | `400` validation or malformed body, `404` not found |
| `DELETE` | `/books/{id}` | `204` no body          | `400` non-integer id, `404` not found            |
| `GET`    | `/health`     | `200` `{"status":"ok"}` | `503` `{"status":"unavailable"}` if the database can't be reached |

Any other method on a known path returns `405` with an `Allow` header. Unknown
paths return `404`.

### Behavior notes

- **Create** (`POST`) requires `title` and `author`. Unknown JSON fields are rejected with `400`, so typos such as `"auther"` fail loudly instead of being dropped.
- **Update** (`PUT`) replaces the whole book. `title` and `author` are required; `year` and `isbn` are cleared if omitted.
- **List** (`GET /books`) returns books in ascending `id` order. `?author=` matches the author case-insensitively and must match the full name. A blank `?author=` is ignored.
- Request bodies are limited to 1 MiB (`413` if exceeded).

### Examples

Create a book:

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"978-0-13-419044-0"}'
```

```json
{"id":1,"title":"The Go Programming Language","author":"Alan A. A. Donovan","year":2015,"isbn":"9780134190440"}
```

List books by an author:

```sh
curl "http://localhost:8080/books?author=alan%20a.%20a.%20donovan"
```

Update a book:

```sh
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language (2nd ed.)","author":"Alan A. A. Donovan"}'
```

Delete a book:

```sh
curl -i -X DELETE http://localhost:8080/books/1
```

Health check:

```sh
curl http://localhost:8080/health
```

## Project layout

```
main.go                   entry point: flags, database open, HTTP server, graceful shutdown
internal/book/           book types, input normalization, validation, ISBN checksums
internal/store/          SQLite persistence (schema, queries)
internal/server/         routing, handlers, JSON request/response helpers
```
