# Book Collection API

A REST API for managing a book collection, written in Go with SQLite storage.

## Requirements

- Go 1.21+

## Setup & Run

```bash
# Install dependencies
go mod download

# Run the server (listens on :8080, creates books.db in current directory)
go run .
```

## Run Tests

```bash
go test ./...
```

## Build

```bash
go build -o bookapi .
./bookapi
```

## Endpoints

| Method | Path           | Description                        |
|--------|----------------|------------------------------------|
| GET    | /health        | Health check                       |
| POST   | /books         | Create a book                      |
| GET    | /books         | List all books (supports ?author=) |
| GET    | /books/{id}    | Get a book by ID                   |
| PUT    | /books/{id}    | Update a book                      |
| DELETE | /books/{id}    | Delete a book                      |

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all books
curl http://localhost:8080/books

# Filter by author
curl "http://localhost:8080/books?author=Donovan%20%26%20Kernighan"

# Get a book by ID
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Same Author","year":2016}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Book Fields

| Field  | Type   | Required | Description        |
|--------|--------|----------|--------------------|
| title  | string | yes      | Book title         |
| author | string | yes      | Author name        |
| year   | int    | no       | Publication year   |
| isbn   | string | no       | ISBN number        |
