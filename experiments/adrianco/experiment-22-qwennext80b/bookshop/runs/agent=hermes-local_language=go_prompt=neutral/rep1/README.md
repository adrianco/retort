# Book API REST Service

A RESTful API service for managing a book collection, built with Go, gorilla/mux, and SQLite.

## Features

- Create, read, update, and delete books
- List all books with optional author filter
- Health check endpoint
- SQLite persistent storage
- Input validation

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /books | List all books (supports ?author= filter) |
| POST | /books | Create a new book |
| GET | /books/{id} | Get a single book by ID |
| PUT | /books/{id} | Update a book |
| DELETE | /books/{id} | Delete a book |

## Book Model

```json
{
  "id": 1,
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "978-0-123456-78-9"
}
```

## Requirements

- Go 1.21 or higher
- SQLite3 library

## Installation

1. Clone or navigate to the project directory:
```bash
cd bookapi
```

2. Download dependencies:
```bash
go mod download
```

## Running the Server

Start the server:
```bash
go run main.go
```

The server will start on `http://localhost:8080`.

## API Usage Examples

### Create a Book
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

### List All Books
```bash
curl http://localhost:8080/books
```

### List Books by Author
```bash
curl "http://localhost:8080/books?author=Fit"
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
    "id": 1,
    "title": "The Great Gatsby (Updated)",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check
```bash
curl http://localhost:8080/health
```

## Running Tests

Run all tests:
```bash
go test ./test/...
```

Run tests with verbose output:
```bash
go test -v ./test/...
```

## Project Structure

```
bookapi/
├── main.go              # Application entry point
├── go.mod               # Go module file
├── go.sum               # Go dependencies checksum
├── model/
│   └── book.go          # Book model and store
├── handler/
│   └── book_handler.go  # HTTP handlers
└── test/
    └── api_test.go      # Integration tests
└── README.md            # This file
```

## Error Response Format

```json
{
  "error": "error message",
  "code": "400",
  "message": "error message"
}
```

## License

MIT License
