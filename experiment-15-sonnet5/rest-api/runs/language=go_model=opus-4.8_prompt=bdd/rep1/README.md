# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library `net/http` router (Go 1.22+ method/path patterns) and a
pure-Go embedded SQLite database ([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite),
no cgo required).

## Requirements

- Go 1.22 or newer (developed against Go 1.26)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (creates ./books.db on first start)
go run .
```

The server listens on `:8080` by default. Override via environment variables:

| Variable       | Default     | Description                                   |
| -------------- | ----------- | --------------------------------------------- |
| `BOOKAPI_ADDR` | `:8080`     | Address/port to listen on                     |
| `BOOKAPI_DSN`  | `books.db`  | SQLite path; use `:memory:` for ephemeral DB  |

Build a binary instead:

```bash
go build -o bookapi .
./bookapi
```

## API

All request and response bodies are JSON.

| Method   | Path           | Description                              | Success |
| -------- | -------------- | ---------------------------------------- | ------- |
| `GET`    | `/health`      | Health check                             | 200     |
| `POST`   | `/books`       | Create a book                            | 201     |
| `GET`    | `/books`       | List books (optional `?author=` filter)  | 200     |
| `GET`    | `/books/{id}`  | Fetch a book by ID                       | 200     |
| `PUT`    | `/books/{id}`  | Update a book                            | 200     |
| `DELETE` | `/books/{id}`  | Delete a book                            | 204     |

### Book fields

```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

`title` and `author` are required. Requests that omit either are rejected with
`400 Bad Request` and an error message. Unknown or missing books return
`404 Not Found`.

### Example requests

```bash
# Create
curl -s -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'

# List all
curl -s localhost:8080/books

# List by author
curl -s 'localhost:8080/books?author=Donovan'

# Get one
curl -s localhost:8080/books/1

# Update
curl -s -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language (Revised)","author":"Donovan","year":2016,"isbn":"978-0134190440"}'

# Delete
curl -s -X DELETE localhost:8080/books/1 -i
```

## Tests

The test suite uses an in-memory SQLite database and exercises the HTTP layer
end to end. Tests follow a BDD (Given/When/Then) style and are named after
observable behaviours.

```bash
go test ./...
go test -v ./...   # see individual scenario names
```

## Project layout

| File             | Responsibility                                  |
| ---------------- | ----------------------------------------------- |
| `main.go`        | Process entrypoint, configuration, HTTP server  |
| `server.go`      | HTTP routing, handlers, validation              |
| `store.go`       | SQLite-backed persistence (CRUD)                |
| `book.go`        | The `Book` model                                |
| `server_test.go` | BDD-style behaviour tests                        |
