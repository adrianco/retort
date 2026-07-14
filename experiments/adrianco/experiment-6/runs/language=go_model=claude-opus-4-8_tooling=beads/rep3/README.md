# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library (`net/http`) for routing and a pure-Go SQLite driver
([`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)) for storage. No
CGO is required.

## Requirements

- Go 1.22 or newer (uses method-aware `net/http` route patterns)

## Setup & Run

```bash
# Fetch dependencies (only needed once)
go mod download

# Run the server (defaults: listens on :8080, stores data in ./books.db)
go run .
```

Configuration via environment variables:

| Variable  | Default     | Description                                  |
|-----------|-------------|----------------------------------------------|
| `ADDR`    | `:8080`     | Address the HTTP server listens on           |
| `DB_PATH` | `books.db`  | SQLite database file path (`:memory:` for in-memory) |

Example:

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

You can also build a binary:

```bash
go build -o bookapi .
./bookapi
```

## API

All request and response bodies are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "441" }
```

`title` and `author` are **required** on create/update; `year` and `isbn` are
optional.

| Method   | Path           | Description                          | Success |
|----------|----------------|--------------------------------------|---------|
| `GET`    | `/health`      | Health check                         | 200     |
| `POST`   | `/books`       | Create a book                        | 201     |
| `GET`    | `/books`       | List books (optional `?author=` filter) | 200 |
| `GET`    | `/books/{id}`  | Get a single book                    | 200     |
| `PUT`    | `/books/{id}`  | Update a book                        | 200     |
| `DELETE` | `/books/{id}`  | Delete a book                        | 204     |

Error responses use appropriate status codes (`400` invalid input/JSON,
`404` not found, `500` server error) and a JSON body of the form
`{"error": "..."}`.

### Examples

```bash
# Create
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"441"}'

# List all / filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune (rev)","author":"Herbert","year":1965,"isbn":"441"}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The test suite (`server_test.go`) runs against an in-memory SQLite database and
covers the health check, create + validation, listing with the author filter,
fetch, update, delete, and not-found behavior.

## Project Layout

| File             | Responsibility                                   |
|------------------|--------------------------------------------------|
| `main.go`        | Entry point, configuration, server startup       |
| `server.go`      | HTTP routing, handlers, JSON helpers              |
| `book.go`        | `Book` model, validation, SQLite-backed `Store`   |
| `server_test.go` | Integration tests                                 |
