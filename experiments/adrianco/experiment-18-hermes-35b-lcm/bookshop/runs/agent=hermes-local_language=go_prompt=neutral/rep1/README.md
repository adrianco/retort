# Book API - REST Service in Go

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Go 1.21 or later

## Setup and Run

```bash
# Build the application
go build -o book-api

# Run the server
./book-api
```

The server starts on port 8080.

## Testing

```bash
go test -v ./...
```

All tests run against an in-memory SQLite database.

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=F.+Scott+Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Revised)","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Validation

- `title` is required
- `author` is required
- Missing fields return a 400 Bad Request with a list of validation errors

## License

MIT
