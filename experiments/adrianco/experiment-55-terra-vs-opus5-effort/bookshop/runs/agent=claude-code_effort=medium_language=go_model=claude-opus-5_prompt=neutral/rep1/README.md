# Book Collection API

A small REST service for managing a book collection, written in Go with the
standard library `net/http` router and backed by SQLite.

- **Language / framework:** Go 1.26, standard-library `net/http` (method + wildcard routing, Go 1.22+)
- **Database:** SQLite via [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) — a pure-Go driver, so no cgo or system SQLite install is needed

## Setup

```bash
go mod download   # dependencies are already pinned in go.mod / go.sum
go build ./...
```

## Run

```bash
go run .
# or
go build -o bookapi . && ./bookapi
```

The server listens on `:8080` and stores data in `./books.db`, both configurable:

| Variable  | Default    | Meaning                                     |
| --------- | ---------- | ------------------------------------------- |
| `ADDR`    | `:8080`    | Listen address                              |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral) |

```bash
ADDR=:9000 DB_PATH=/var/lib/books.db ./bookapi
```

The schema is created automatically on startup, and the process shuts down
gracefully on `SIGINT` / `SIGTERM`.

## Test

```bash
go test ./...
go test -v -race ./...   # verbose, with the race detector
```

## API

All responses are JSON (`application/json; charset=utf-8`), except `204 No Content`.

### `GET /health`

```bash
curl localhost:8080/health
# 200 {"status":"ok"}
```

Returns `503` with `{"status":"unhealthy",...}` if the database is unreachable.

### `POST /books`

Creates a book. `title` and `author` are required and must be non-blank;
`year` and `isbn` are optional. Unknown JSON fields are rejected.

```bash
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

```
201 Created
Location: /books/1
{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}
```

### `GET /books`

Lists all books, ordered by ID. Optional `?author=` filter matches the author
exactly, case-insensitively. Always returns an array (`[]` when empty).

```bash
curl 'localhost:8080/books'
curl 'localhost:8080/books?author=Frank%20Herbert'
# 200 [{"id":1,"title":"Dune",...}]
```

### `GET /books/{id}`

```bash
curl localhost:8080/books/1
# 200 {"id":1,"title":"Dune",...}
# 404 {"error":"book not found"}
```

### `PUT /books/{id}`

Full replacement — the same validation rules as `POST` apply, so send every
field you want to keep.

```bash
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"new-isbn"}'
# 200 {"id":1,...,"isbn":"new-isbn"}
```

### `DELETE /books/{id}`

```bash
curl -i -X DELETE localhost:8080/books/1
# 204 No Content   (404 if the book does not exist)
```

## Status codes

| Code | When                                                              |
| ---- | ----------------------------------------------------------------- |
| 200  | Successful `GET` / `PUT`                                          |
| 201  | Book created (with a `Location` header)                           |
| 204  | Book deleted                                                      |
| 400  | Validation failure, malformed/empty JSON, or a non-numeric `id`   |
| 404  | No book with that ID                                              |
| 405  | Method not supported on that path                                 |
| 500  | Unexpected server-side error                                      |
| 503  | Health check failed                                               |

Validation errors name the offending fields:

```json
{ "error": "validation failed", "fields": { "title": "is required" } }
```

## Layout

| File             | Contents                                                  |
| ---------------- | --------------------------------------------------------- |
| `main.go`        | Configuration, startup, graceful shutdown                 |
| `server.go`      | Routes, HTTP handlers, JSON and error rendering            |
| `store.go`       | SQLite schema and CRUD queries                            |
| `book.go`        | `Book` model and input validation                         |
| `server_test.go` | Integration tests driving the HTTP handlers end-to-end     |
| `store_test.go`  | Store-level tests, including on-disk persistence          |

Tests run against an in-memory SQLite database (plus one temp-file test that
verifies data survives a reopen), so they need no external setup and leave
nothing behind.
