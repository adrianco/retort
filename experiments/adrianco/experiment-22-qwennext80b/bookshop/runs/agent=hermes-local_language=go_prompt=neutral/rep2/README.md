# Book API REST Service

A REST API service for managing a book collection built with Go, Gorilla Mux, and SQLite.

## Features

- **Health Check**: `GET /health` - Returns service health status
- **List Books**: `GET /books` - List all books (supports `?author=` filter)
- **Get Book**: `GET /books/{id}` - Get a single book by ID
- **Create Book**: `POST /books` - Create a new book
- **Update Book**: `PUT /books/{id}` - Update an existing book
- **Delete Book**: `DELETE /books/{id}` - Delete a book

## Requirements

- Go 1.18 or higher
- SQLite3 development libraries

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
go mod download
```

## Build

```bash
go build -o book-api cmd/main.go
```

## Run

```bash
# Run with default port 8080
./book-api

# Or specify a custom port
PORT=3000 ./book-api
```

The server will start on `http://localhost:8080` (or the specified port).

## API Usage Examples

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{"status":"healthy"}
```

### Create a Book

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

### List All Books

```bash
curl http://localhost:8080/books
```

### List Books by Author

```bash
curl "http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan"
```

### Get a Single Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Go Programming Language (Updated)",
    "author": "Alan A. A. Donovan",
    "year": 2016,
    "isbn": "978-0134190440"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Input Validation

- **Title**: Required (cannot be empty)
- **Author**: Required (cannot be empty)
- **Year**: Optional
- **ISBN**: Optional

## Testing

Run the test suite:

```bash
go test -v ./...
```

Run tests for specific packages:

```bash
go test -v ./internal/handler
go test -v ./internal/model
```

## Project Structure

```
book-api/
├── cmd/
│   └── main.go          # Application entry point
├── internal/
│   ├── handler/         # HTTP handlers
│   │   └── book_handler.go
│   ├── model/           # Data models
│   │   └── book.go
│   ├── migrate/         # Database migrations
│   │   └── migrate.go
│   └── repository/      # Data access layer
├── go.mod
├── go.sum
└── README.md
```

## License

MIT
