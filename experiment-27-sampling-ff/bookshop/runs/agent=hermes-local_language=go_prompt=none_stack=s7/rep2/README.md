# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite3 (the go-sqlite3 driver uses CGO, so ensure you have a C compiler installed)

## Setup and Run

1. Install dependencies:
   ```bash
   go mod tidy
   ```

2. Run the server:
   ```bash
   go run app.go
   ```

   The server will start on `http://localhost:8080`

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
curl "http://localhost:8080/books?author=Donovan"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","year":2024}'
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
go test -v
```

## API Response Format

All responses are in JSON format. Successful responses return the appropriate HTTP status code (200, 201, 204). Error responses include an "error" field with a description.

### Example Success Response (POST /books)
```json
{
  "id": 1,
  "title": "The Go Programming Language",
  "author": "Alan Donovan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

### Example Error Response
```json
{
  "error": "Book not found with ID 1"
}
```
