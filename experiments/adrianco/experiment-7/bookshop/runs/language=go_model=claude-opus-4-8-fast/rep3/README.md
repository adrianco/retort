# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library's `net/http` router (Go 1.22+ method/path patterns) and a
pure-Go SQLite backend ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
no CGO required).

## Requirements

- Go 1.22 or newer (developed/tested with Go 1.26)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (creates books.db in the working directory)
go run .
```

The server listens on `:8080` by default. Override with environment variables:

| Variable  | Default    | Description                         |
|-----------|------------|-------------------------------------|
| `ADDR`    | `:8080`    | Listen address                      |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` works) |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

To build a binary:

```bash
go build -o bookapi .
./bookapi
```

## Tests

```bash
go test ./...
```

The suite uses an in-memory SQLite database and `httptest` to exercise the
handlers end-to-end (health check, create/get, validation, author filter,
update, delete, and not-found cases).

## API

All responses are JSON. `title` and `author` are required on create and update.

### `GET /health`
Health check.
```json
200 OK
{ "status": "ok" }
```

### `POST /books`
Create a book.
```bash
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"9780134190440"}'
```
```json
201 Created
{ "id": 1, "title": "The Go Programming Language", "author": "Donovan & Kernighan", "year": 2015, "isbn": "9780134190440" }
```
Returns `400 Bad Request` if the JSON is invalid or `title`/`author` is missing.

### `GET /books`
List all books. Optional `?author=` filter (exact match).
```bash
curl localhost:8080/books
curl 'localhost:8080/books?author=Donovan%20%26%20Kernighan'
```
```json
200 OK
[ { "id": 1, "title": "...", "author": "...", "year": 2015, "isbn": "..." } ]
```

### `GET /books/{id}`
Fetch a single book. Returns `404 Not Found` if it does not exist.

### `PUT /books/{id}`
Replace a book. Same body and validation as create. Returns `404 Not Found`
for an unknown id.
```bash
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"Same Author","year":2016,"isbn":"123"}'
```

### `DELETE /books/{id}`
Delete a book. Returns `204 No Content` on success, `404 Not Found` if it does
not exist.

## Status codes

| Code | Meaning                                            |
|------|----------------------------------------------------|
| 200  | OK (get, list, update)                             |
| 201  | Created                                            |
| 204  | No Content (delete)                               |
| 400  | Bad request (invalid JSON / id, missing required) |
| 404  | Book not found                                     |
| 500  | Internal server error                             |

## Project layout

| File            | Responsibility                              |
|-----------------|---------------------------------------------|
| `main.go`       | Entry point, configuration, server startup  |
| `handlers.go`   | HTTP routing, request decoding, responses   |
| `store.go`      | SQLite persistence (CRUD)                    |
| `model.go`      | Data types and input validation             |
| `main_test.go`  | Integration tests                           |
