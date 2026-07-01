# Book Collection API

A REST API for managing a book collection, built with Go's standard
`net/http` library and a SQLite-backed store (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver, so no
CGO or system SQLite library is required).

## Requirements

- Go 1.22+ (uses the standard-library `http.ServeMux` method/path routing)

## Setup

```bash
go mod download
```

## Run

```bash
go run .
```

By default the server listens on `:8080` and stores data in `./books.db`.
Both can be overridden with environment variables:

```bash
BOOKAPI_ADDR=:9090 BOOKAPI_DB=mybooks.db go run .
```

## API

| Method | Path             | Description                              |
|--------|------------------|-------------------------------------------|
| GET    | `/health`        | Health check                              |
| POST   | `/books`         | Create a book                             |
| GET    | `/books`         | List all books (optional `?author=` filter) |
| GET    | `/books/{id}`    | Get a single book                         |
| PUT    | `/books/{id}`    | Update a book                             |
| DELETE | `/books/{id}`    | Delete a book                             |

A book has the shape:

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required on create/update; omitting either returns
`400 Bad Request`. Requests for a book ID that doesn't exist return
`404 Not Found`.

### Examples

```bash
# Create a book
curl -X POST localhost:8080/books \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all books
curl localhost:8080/books

# Filter by author
curl 'localhost:8080/books?author=Frank+Herbert'

# Get a single book
curl localhost:8080/books/1

# Update a book
curl -X PUT localhost:8080/books/1 \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"new-isbn"}'

# Delete a book
curl -X DELETE localhost:8080/books/1
```

## Tests

```bash
go test ./...
```

Tests use an in-memory SQLite database (`:memory:`) and `httptest`, so they
run without touching the filesystem or network.

## Project layout

- `main.go` — entrypoint, wiring, and config
- `models.go` — `Book` type and validation
- `store.go` — SQLite-backed data access layer
- `handlers.go` — HTTP handlers and routing
- `handlers_test.go` — integration tests over the HTTP layer
