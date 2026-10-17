# Book Collection API

A REST API for managing a book collection, written in Go with the standard
library's `net/http` router and an embedded SQLite database. The SQLite driver
is [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), which is pure
Go, so no C compiler is needed.

## Requirements

- Go 1.26 or later (see `go.mod`)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

Or build a binary and run it:

```sh
go build -o bookapi .
./bookapi -addr :8080 -db books.db
```

| Flag    | Default    | Description                              |
|---------|------------|------------------------------------------|
| `-addr` | `:8080`    | HTTP listen address                      |
| `-db`   | `books.db` | Path to the SQLite database file (created if missing) |

The server shuts down gracefully on `Ctrl+C` or `SIGTERM`.

## Test

```sh
go test ./...
```

The suite includes unit tests for validation, store tests against a real SQLite
file, and HTTP integration tests that exercise every endpoint.

## Data model

| Field    | Type    | Required | Notes                                                    |
|----------|---------|----------|----------------------------------------------------------|
| `id`     | integer | (server) | Assigned on create; ignored if sent by a client          |
| `title`  | string  | yes      | Non-blank after trimming whitespace                      |
| `author` | string  | yes      | Non-blank after trimming whitespace                      |
| `year`   | integer | no       | `0` or omitted means unknown; otherwise 1 to next year   |
| `isbn`   | string  | no       | If present, a valid ISBN-10 or ISBN-13 (hyphens/spaces allowed) |

## API

All requests and responses use JSON. Errors are returned as `{"error": "..."}`.

### `POST /books`: create a book

```sh
curl -i -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-306-40615-7"}'
```

- `201 Created` with the new book and a `Location: /books/{id}` header.
- `422 Unprocessable Entity` if validation fails. The response lists each bad
  field under `fields`:

  ```json
  {"error":"validation failed","fields":{"author":"author is required","title":"title is required"}}
  ```

- `400 Bad Request` if the body is not valid JSON or contains more than one
  JSON value.

### `GET /books`: list books

Returns a JSON array ordered by `id`; an empty collection returns `[]`.

Optional query parameter `author` filters to books by that author. The match is
exact but case-insensitive, so `?author=frank herbert` matches "Frank Herbert".

```sh
curl "http://localhost:8080/books?author=Frank%20Herbert"
```

### `GET /books/{id}`: get one book

- `200 OK` with the book.
- `404 Not Found` if no book has that ID.
- `400 Bad Request` if `{id}` is not a positive integer.

### `PUT /books/{id}`: replace a book

The request body is a full replacement, so it must include `title` and `author`
as with create. Omitted `year` and `isbn` are cleared.

```sh
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1966}'
```

- `200 OK` with the updated book.
- `422` on validation failure, `404` if the book does not exist, `400` for a bad
  ID or body.

### `DELETE /books/{id}`: delete a book

- `204 No Content` on success.
- `404 Not Found` if the book does not exist.

### `GET /health`: health check

- `200 OK` with `{"status":"ok"}` when the database is reachable.
- `503 Service Unavailable` with `{"status":"unavailable"}` otherwise.

```sh
curl http://localhost:8080/health
```

Requests with an unsupported method on a known path (for example `PATCH
/books/1`) receive `405 Method Not Allowed`.

## Project layout

| File            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `main.go`       | Flags, startup, graceful shutdown                    |
| `server.go`     | Routes, HTTP handlers, JSON helpers                  |
| `book.go`       | Book model, normalization, validation (incl. ISBN check digits) |
| `store.go`      | SQLite persistence and schema                        |
| `*_test.go`     | Unit, store, and HTTP integration tests              |
