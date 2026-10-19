# Book API

A REST API service for managing a book collection, built with Go.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

All responses are in JSON format with appropriate HTTP status codes.

## Setup

1. Ensure Go 1.20+ is installed
2. Clone or navigate to the project directory
3. Download dependencies:

```bash
go mod tidy
```

## Running

```bash
go run main.go
```

The server will start on `http://localhost:8080`.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=Alan Donovan"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language, Second Edition"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Running Tests

```bash
go test -v
```
