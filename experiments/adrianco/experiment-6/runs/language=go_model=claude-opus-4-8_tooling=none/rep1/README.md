# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` and a pure-Go SQLite database
([modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite) — no cgo required).

## Requirements

- Go 1.21+ (developed with Go 1.26)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (creates ./books.db on first start)
go run .
```

The server listens on `:8080` by default. Configure via environment variables:

| Variable  | Default    | Description                    |
|-----------|------------|--------------------------------|
| `ADDR`    | `:8080`    | Listen address                 |
| `DB_PATH` | `books.db` | SQLite file path (`:memory:` for ephemeral) |

Build a binary instead:

```bash
go build -o bookapi .
./bookapi
```

## Running Tests

```bash
go test ./...
```

Tests run against an in-memory SQLite database, so they leave no files behind.

## API

All request and response bodies are JSON. `title` and `author` are required on
create and update.

### `GET /health`
Health check. Returns `200` with `{"status":"ok"}`.

### `POST /books`
Create a book.

```bash
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}'
```

- `201 Created` with the created book (including its `id`)
- `400 Bad Request` if `title` or `author` is missing, or the body is invalid

### `GET /books`
List all books. Optional `?author=` filter.

```bash
curl localhost:8080/books
curl "localhost:8080/books?author=Frank%20Herbert"
```

Returns `200` with a JSON array.

### `GET /books/{id}`
Get a single book.

- `200 OK` with the book
- `404 Not Found` if no book has that ID

### `PUT /books/{id}`
Replace a book's fields.

```bash
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780593098233"}'
```

- `200 OK` with the updated book
- `400 Bad Request` on validation failure
- `404 Not Found` if the book does not exist

### `DELETE /books/{id}`
Delete a book.

- `204 No Content` on success
- `404 Not Found` if the book does not exist

## Project Layout

| File               | Responsibility                                  |
|--------------------|-------------------------------------------------|
| `main.go`          | Entry point, configuration, server startup      |
| `handlers.go`      | HTTP routing, request/response handling          |
| `store.go`         | SQLite persistence layer                          |
| `models.go`        | Data types and input validation                  |
| `handlers_test.go` | Integration tests covering all endpoints         |
