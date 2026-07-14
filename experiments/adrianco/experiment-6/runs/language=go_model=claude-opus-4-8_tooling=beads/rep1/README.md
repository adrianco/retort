# Book Collection API

A small REST API for managing a book collection, written in Go using only the
standard library's `net/http` router (Go 1.22+ method-based routing). Data is
persisted in an embedded SQLite database via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver (no cgo
required).

## Requirements

- Go 1.22 or newer

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Build
go build -o bookapi .

# Run (defaults: listens on :8080, database file books.db)
./bookapi

# Or run directly
go run .
```

### Configuration

The server is configured via environment variables:

| Variable  | Default    | Description                          |
|-----------|------------|--------------------------------------|
| `ADDR`    | `:8080`    | Address/port to listen on            |
| `DB_PATH` | `books.db` | SQLite database file (use `:memory:` for ephemeral storage) |

Example:

```bash
ADDR=:9000 DB_PATH=/var/lib/books.db ./bookapi
```

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "9780441172719" }
```

`title` and `author` are required on create and update.

| Method | Path           | Description                          | Success |
|--------|----------------|--------------------------------------|---------|
| GET    | `/health`      | Health check                         | 200     |
| POST   | `/books`       | Create a book                        | 201     |
| GET    | `/books`       | List books (`?author=` filter)       | 200     |
| GET    | `/books/{id}`  | Get a book by ID                     | 200     |
| PUT    | `/books/{id}`  | Update a book                        | 200     |
| DELETE | `/books/{id}`  | Delete a book                        | 204     |

Error responses use the form `{"errors": ["message", ...]}`. Status codes:
`400` for invalid input/JSON, `404` for a missing book, `500` for server errors.

### Examples

```bash
# Health check
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Herbert","year":1965,"isbn":"9780441172719"}'

# List all / filter by author
curl localhost:8080/books
curl 'localhost:8080/books?author=Herbert'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune Messiah","author":"Herbert","year":1969}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

The test suite (`handlers_test.go`) covers the health check, create + read,
input validation, the author filter, update (including 404), delete (including
404), and invalid-ID handling, running against an in-memory database.

## Project layout

| File                | Responsibility                              |
|---------------------|---------------------------------------------|
| `main.go`           | Entry point, configuration, server startup  |
| `models.go`         | `Book` / `BookInput` types and validation   |
| `store.go`          | SQLite persistence layer                     |
| `handlers.go`       | HTTP routing and request handlers           |
| `handlers_test.go`  | Integration tests                           |
