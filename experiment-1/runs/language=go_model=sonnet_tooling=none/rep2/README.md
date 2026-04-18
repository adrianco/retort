# Book Collection API

A REST API for managing a book collection, written in Go with SQLite storage.

## Requirements

- Go 1.22 or later

## Setup & Run

```bash
go run .
```

The server starts on port `8080`. The SQLite database is stored in `books.db` in the current directory.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /books | Create a book |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/{id} | Get a book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

### Book fields

| Field | Type | Required |
|-------|------|----------|
| title | string | yes |
| author | string | yes |
| year | integer | no |
| isbn | string | no |

### Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Alan+Donovan"

# Get a book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"Updated Title","author":"Alan Donovan"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Tests

```bash
go test ./...
```
