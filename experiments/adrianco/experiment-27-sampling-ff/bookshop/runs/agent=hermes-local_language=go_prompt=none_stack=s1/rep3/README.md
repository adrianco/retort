# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite3

## Setup

1. Clone or navigate to the project directory.

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Run the application:
   ```bash
   go run app.go
   ```

The API will be available at `http://localhost:8080`.

## Usage Examples

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
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
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

Run the unit tests:
```bash
go test -v
```

## API Response Format

All responses are in JSON format.

### Success Response (201 Created)
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "title and author are required"
}
```

### Not Found Response (404 Not Found)
```json
{
  "error": "book not found"
}
```
