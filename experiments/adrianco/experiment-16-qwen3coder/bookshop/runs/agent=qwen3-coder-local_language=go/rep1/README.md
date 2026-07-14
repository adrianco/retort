# Book Collection REST API

A simple REST API service for managing a book collection with SQLite backend.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Setup

1. Make sure you have Go installed (version 1.21 or higher)
2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Run

```bash
go run main.go
```

The server will start on port 8080 by default, or use the PORT environment variable.

## Testing

Run the tests with:
```bash
go test -v
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl http://localhost:8080/books?author=Fitzgerald
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Revised Edition",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```