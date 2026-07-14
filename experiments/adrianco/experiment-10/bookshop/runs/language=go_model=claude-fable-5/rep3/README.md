# Book API

A REST API service for managing a book collection, written in Go using the
standard library `net/http` router and SQLite for storage (via
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite), a pure-Go
driver — no CGO or system SQLite required).

## Requirements

- Go 1.22 or later (developed with Go 1.26)

## Setup and run

```sh
go mod download   # fetch dependencies (first run only)
go run .
```

The server listens on `:8080` and stores data in `books.db` in the current
directory by default. Both are configurable via environment variables:

```sh
ADDR=:9000 BOOKS_DB=/tmp/mybooks.db go run .
```

## Run the tests

```sh
go test ./...
```

Tests run against an in-memory SQLite database and cover the health check,
CRUD operations, input validation, author filtering, and not-found/invalid-ID
error cases.

## API

A book looks like:

```json
{"id": 1, "title": "Sun Performance and Tuning", "author": "Adrian Cockcroft", "year": 1998, "isbn": "978-0130952493"}
```

`title` and `author` are required; `year` and `isbn` are optional. Errors are
returned as `{"error": "message"}`.

| Method | Path             | Description                          | Status codes        |
|--------|------------------|--------------------------------------|---------------------|
| GET    | `/health`        | Health check                         | 200                 |
| POST   | `/books`         | Create a book                        | 201, 400            |
| GET    | `/books`         | List books, optional `?author=` filter (exact match) | 200 |
| GET    | `/books/{id}`    | Get one book                         | 200, 400, 404       |
| PUT    | `/books/{id}`    | Replace a book (same body as POST)   | 200, 400, 404       |
| DELETE | `/books/{id}`    | Delete a book                        | 204, 400, 404       |

### Examples

```sh
# Create
curl -X POST localhost:8080/books \
  -d '{"title":"Sun Performance and Tuning","author":"Adrian Cockcroft","year":1998,"isbn":"978-0130952493"}'

# List all / filter by author
curl localhost:8080/books
curl "localhost:8080/books?author=Adrian%20Cockcroft"

# Get, update, delete
curl localhost:8080/books/1
curl -X PUT localhost:8080/books/1 -d '{"title":"New Title","author":"Adrian Cockcroft"}'
curl -X DELETE localhost:8080/books/1
```

## Project layout

- `main.go` — entry point, config, server startup
- `handlers.go` — HTTP routing, handlers, validation
- `store.go` — SQLite storage layer and `Book` model
- `api_test.go` — integration tests over the full HTTP stack
