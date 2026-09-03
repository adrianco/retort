# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation (title and author required)
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.21+
- SQLite3

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Service

```bash
go run main.go
```

The service will start on port 8080 by default. You can change the port by setting the `PORT` environment variable:

```bash
PORT=8081 go run main.go
```

## Testing

Run the tests with:

```bash
go test
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language", "author":"Alan A. A. Donovan", "year":2015, "isbn":"9780134190440"}'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl http://localhost:8080/books?author=Donovan
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language", "author":"Alan A. A. Donovan", "year":2016, "isbn":"9780134190440"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```