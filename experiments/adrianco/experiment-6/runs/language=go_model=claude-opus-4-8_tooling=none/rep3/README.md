# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` router (Go 1.22+) and a pure-Go SQLite backend
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) — no CGO required).

## Requirements

- Go 1.22 or newer

## Setup & Run

```bash
go mod download   # fetch dependencies
go run .          # build and start the server
```

The server listens on `:8080` by default and stores data in `books.db`.
Both are configurable via environment variables:

| Variable  | Default     | Description                                   |
|-----------|-------------|-----------------------------------------------|
| `ADDR`    | `:8080`     | Address/port to listen on                     |
| `DB_PATH` | `books.db`  | SQLite file path (use `:memory:` for ephemeral) |

```bash
ADDR=":9000" DB_PATH="/tmp/library.db" go run .
```

## API

All request and response bodies are JSON.

### `GET /health`
Health check.
```bash
curl localhost:8080/health
# {"status":"ok"}
```

### `POST /books`
Create a book. `title` and `author` are required.
```bash
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"9781617291784"}'
# 201 Created
# {"id":1,"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"9781617291784"}
```

### `GET /books`
List all books. Optional `?author=` filter (exact match).
```bash
curl localhost:8080/books
curl "localhost:8080/books?author=Kennedy"
```

### `GET /books/{id}`
Fetch a single book.
```bash
curl localhost:8080/books/1
```

### `PUT /books/{id}`
Update a book (`title` and `author` required).
```bash
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go in Action, 2nd Ed","author":"Kennedy","year":2020,"isbn":"123"}'
```

### `DELETE /books/{id}`
Delete a book.
```bash
curl -X DELETE localhost:8080/books/1
# 204 No Content
```

### Status codes

| Code | Meaning                                  |
|------|------------------------------------------|
| 200  | OK (get / list / update)                 |
| 201  | Created                                  |
| 204  | No Content (delete)                      |
| 400  | Bad request (invalid JSON / validation)  |
| 404  | Book not found                           |
| 500  | Internal server error                    |

## Tests

```bash
go test ./...
```

The test suite (`handlers_test.go`) runs against an in-memory database and
covers the health check, create + fetch, input validation, the author filter,
update, delete, and not-found behavior.

## Project layout

| File               | Responsibility                          |
|--------------------|-----------------------------------------|
| `main.go`          | Entry point, config, server startup     |
| `handlers.go`      | HTTP routing and request handlers       |
| `store.go`         | SQLite persistence layer                |
| `models.go`        | Data types and validation               |
| `handlers_test.go` | Integration tests                       |
