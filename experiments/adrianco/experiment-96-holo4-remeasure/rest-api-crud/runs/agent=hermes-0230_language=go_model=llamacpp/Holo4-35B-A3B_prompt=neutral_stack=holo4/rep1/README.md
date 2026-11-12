# Book API

A REST API service for managing a book collection, built in Go with SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Setup

1. Ensure Go 1.26+ is installed.
2. Clone or navigate to the project directory.
3. Download dependencies:
   ```bash
   go mod tidy
   ```

## Running

```bash
go run .
```

The server starts on `http://localhost:8080`.

## API Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=Donovan"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2016,"isbn":"978-0134190440"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Running Tests

```bash
go test -v ./...
```
