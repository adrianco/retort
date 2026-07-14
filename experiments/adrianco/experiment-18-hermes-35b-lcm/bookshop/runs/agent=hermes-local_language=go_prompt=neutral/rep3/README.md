# Book API REST Service

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book (partial updates supported)
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.22 or later

## Setup and Run

```bash
# Clone or navigate to the project directory
cd bookapi

# Download dependencies
go mod download

# Run the server
go run .

# Or set custom port and database path
PORT=3000 DB_PATH=mybooks.db go run .
```

The server starts on port 8080 by default.

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Alan+Donovan"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language (2nd Edition)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Testing

Run all tests:

```bash
go test -v ./...
```

## Response Examples

### Success (201 Created)
```json
{
  "message": "book created",
  "book": {
    "id": 1,
    "title": "The Go Programming Language",
    "author": "Alan Donovan",
    "year": 2015,
    "isbn": "978-0134190440",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Validation Error (400 Bad Request)
```json
{
  "error": "validation failed",
  "validations": [
    {"field": "title", "message": "title is required"},
    {"field": "author", "message": "author is required"}
  ]
}
```

### Not Found (404)
```json
{
  "error": "book not found"
}
```
