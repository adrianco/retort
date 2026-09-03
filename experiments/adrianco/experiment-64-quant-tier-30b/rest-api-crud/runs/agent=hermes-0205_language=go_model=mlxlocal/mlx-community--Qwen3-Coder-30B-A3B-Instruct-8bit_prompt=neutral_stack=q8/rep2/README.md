# Book API Service

A REST API service for managing a book collection implemented in Go with SQLite storage.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.16 or higher
- SQLite3

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

The server will start on `http://localhost:8080`.

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
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan",
    "year": 2015,
    "isbn": "978-0134190440"
  }'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl "http://localhost:8080/books?author=Donovan"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language",
    "author": "Alan A. A. Donovan & Brian W. Kernighan",
    "year": 2015,
    "isbn": "978-0134190440"
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