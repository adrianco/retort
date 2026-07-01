# Book Collection API

A REST API for managing a book collection, written in Go using the standard
library `net/http` and a SQLite-backed store (via the pure-Go
[`modernc.org/sqlite`](https://pkg.go.dev/modernc.org/sqlite) driver, so no
CGO or system SQLite install is required).

## Requirements

- Go 1.22+ (uses the standard library's method/path routing in `net/http.ServeMux`)

## Setup

```sh
go mod download
```

## Run

```sh
go run .
```

By default the server listens on `:8080` and stores data in `./books.db`.
Both are configurable via environment variables:

```sh
BOOKAPI_ADDR=:9090 BOOKAPI_DB_PATH=/tmp/books.db go run .
```

## Test

```sh
go test ./...
```

## API

| Method | Path          | Description                          |
|--------|---------------|---------------------------------------|
| GET    | `/health`     | Health check                          |
| POST   | `/books`      | Create a book                         |
| GET    | `/books`      | List all books (optional `?author=`) |
| GET    | `/books/{id}` | Get a single book                     |
| PUT    | `/books/{id}` | Update a book                         |
| DELETE | `/books/{id}` | Delete a book                         |

### Book object

```json
{
  "id": 1,
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "isbn": "978-0441013593"
}
```

`title` and `author` are required on create/update requests; omitting either
returns `400 Bad Request`.

### Example requests

```sh
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=Frank+Herbert"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"978-0441172719"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

### Status codes

- `200 OK` — successful GET/PUT
- `201 Created` — successful POST
- `204 No Content` — successful DELETE
- `400 Bad Request` — invalid JSON, missing required fields, or invalid ID
- `404 Not Found` — book does not exist

## Project layout

- `book.go` — `Book` model
- `store.go` — SQLite-backed persistence layer
- `handlers.go` — HTTP handlers and routing
- `main.go` — server entry point
- `store_test.go` / `handlers_test.go` — unit and integration tests
