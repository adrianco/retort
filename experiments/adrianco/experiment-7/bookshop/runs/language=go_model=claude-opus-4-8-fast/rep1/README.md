# Book Collection API

A small REST API for managing a collection of books, written in Go using the
standard library `net/http` router (Go 1.22+) and a pure-Go SQLite driver
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite) — no CGO required).

## Requirements

- Go 1.22 or newer (developed against Go 1.26)

## Setup & Run

```sh
# Fetch dependencies (uses the checked-in go.mod / go.sum)
go mod download

# Run the server (listens on :8080 by default, data in ./books.db)
go run .
```

Configuration via environment variables:

| Variable     | Default     | Description                              |
|--------------|-------------|------------------------------------------|
| `BOOKS_ADDR` | `:8080`     | Address the HTTP server listens on       |
| `BOOKS_DB`   | `books.db`  | SQLite path; use `:memory:` for ephemeral |

Example:

```sh
BOOKS_ADDR=:9000 BOOKS_DB=:memory: go run .
```

## Build

```sh
go build -o bookapi .
./bookapi
```

## Run the tests

```sh
go test ./...
```

The tests use an in-memory SQLite database, so they leave no files behind.

## API

All responses are JSON. Errors are returned as `{"error": "message"}`.

### `GET /health`
Health check.

```sh
curl localhost:8080/health
# {"status":"ok"}
```

### `POST /books`
Create a book. `title` and `author` are required.

```sh
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'
```

Responses: `201 Created` with the book, `400 Bad Request` on validation/JSON errors.

### `GET /books`
List all books. Optional `?author=` filter.

```sh
curl localhost:8080/books
curl 'localhost:8080/books?author=Donovan%20%26%20Kernighan'
```

Response: `200 OK` with a JSON array (`[]` when empty).

### `GET /books/{id}`
Fetch a single book.

```sh
curl localhost:8080/books/1
```

Responses: `200 OK`, `404 Not Found`, `400 Bad Request` for a malformed id.

### `PUT /books/{id}`
Update a book. `title` and `author` are required.

```sh
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"Same Author","year":2016,"isbn":"978-0134190440"}'
```

Responses: `200 OK` with the updated book, `404 Not Found`, `400 Bad Request`.

### `DELETE /books/{id}`
Delete a book.

```sh
curl -X DELETE localhost:8080/books/1
```

Responses: `204 No Content`, `404 Not Found`.

## Project layout

| File             | Purpose                                            |
|------------------|----------------------------------------------------|
| `main.go`        | Process entry point, config, server startup        |
| `server.go`      | HTTP routes, handlers, JSON helpers                |
| `store.go`       | SQLite-backed CRUD storage layer                   |
| `models.go`      | `Book` type and input validation                   |
| `server_test.go` | Integration tests covering every endpoint          |
