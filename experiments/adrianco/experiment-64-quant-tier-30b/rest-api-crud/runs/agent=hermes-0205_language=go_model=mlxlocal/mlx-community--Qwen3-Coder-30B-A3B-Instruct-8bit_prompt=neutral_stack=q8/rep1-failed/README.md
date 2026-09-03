# Book API REST Service

A simple REST API for managing a book collection built with Go and Gin.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- SQLite database storage
- Input validation

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.16+

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

The server will start on port 8080 by default. You can override the port by setting the `PORT` environment variable:

```bash
PORT=8081 go run main.go
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
curl http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan
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
    "title": "The Go Programming Language (Updated)",
    "year": 2020
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```