# Book API

A REST API for managing a book collection.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (with optional author filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Ensure Go is installed
2. Run `go mod tidy` to install dependencies
3. Run `go run main.go` to start the server
4. Server will start on port 8080 by default

## Testing

Run tests with `go test ./...`

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'

# List all books
curl http://localhost:8080/books

# Get a specific book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby - Updated", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273565"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```
