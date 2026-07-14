# Book Collection API

A small REST API for managing a book collection, written in Go using the
standard library `net/http` router (Go 1.22+ method/path patterns) and an
embedded SQLite database via the pure-Go [`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite)
driver (no CGO required).

## Requirements

- Go 1.22 or newer (developed against Go 1.26)

## Setup & Run

```bash
# Fetch dependencies
go mod download

# Run the server (defaults: :8080, books.db)
go run .
```

Configuration via environment variables:

| Variable  | Default    | Description                              |
|-----------|------------|------------------------------------------|
| `ADDR`    | `:8080`    | Listen address                           |
| `DB_PATH` | `books.db` | SQLite file path (use `:memory:` for RAM) |

```bash
ADDR=:9000 DB_PATH=/tmp/books.db go run .
```

## Build

```bash
go build -o bookapi .
./bookapi
```

## Tests

```bash
go test ./...
```

## API

All responses are JSON. A book has the shape:

```json
{ "id": 1, "title": "Go in Action", "author": "Kennedy", "year": 2015, "isbn": "978-1617291784" }
```

| Method   | Path           | Description                          | Success    |
|----------|----------------|--------------------------------------|------------|
| `GET`    | `/health`      | Health check                         | `200`      |
| `POST`   | `/books`       | Create a book                        | `201`      |
| `GET`    | `/books`       | List books (optional `?author=`)     | `200`      |
| `GET`    | `/books/{id}`  | Get a book by ID                     | `200`      |
| `PUT`    | `/books/{id}`  | Update a book                        | `200`      |
| `DELETE` | `/books/{id}`  | Delete a book                        | `204`      |

### Validation & status codes

- `title` and `author` are required on create and update.
- `400 Bad Request` — invalid JSON, missing required fields, or invalid ID.
- `404 Not Found` — no book with the given ID.
- `500 Internal Server Error` — unexpected database error.

Error responses use the form:

```json
{ "errors": ["title is required", "author is required"] }
```

### Examples

```bash
# Health
curl localhost:8080/health

# Create
curl -X POST localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"978-1617291784"}'

# List (all / filtered by author)
curl localhost:8080/books
curl 'localhost:8080/books?author=Kennedy'

# Get one
curl localhost:8080/books/1

# Update
curl -X PUT localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Go in Action, 2nd ed","author":"Kennedy","year":2019,"isbn":"978-1617291784"}'

# Delete
curl -X DELETE localhost:8080/books/1
```

## Project layout

| File               | Purpose                                   |
|--------------------|-------------------------------------------|
| `main.go`          | Entry point, config, server bootstrap     |
| `models.go`        | `Book` type, input payload, validation    |
| `store.go`         | SQLite-backed data access layer           |
| `handlers.go`      | HTTP routes and handlers                  |
| `handlers_test.go` | Integration tests over the HTTP handlers  |
