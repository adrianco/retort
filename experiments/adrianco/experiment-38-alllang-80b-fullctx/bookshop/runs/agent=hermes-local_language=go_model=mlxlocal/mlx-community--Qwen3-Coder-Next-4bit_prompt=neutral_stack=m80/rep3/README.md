# Book API REST Service

A REST API service for managing a book collection using Go, SQLite, and HTTP.

## Features

- POST /books - Create a new book
- GET /books - List all books (supports `?author=` filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Prerequisites

- Go 1.21 or higher
- SQLite3 development libraries

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd book-api

# Install dependencies
go mod tidy

# Build the application
go build -o book-api .
```

## Running

```bash
# Start the server (default port 8080)
./book-api

# Or specify a custom port
PORT=3000 ./book-api
```

The server will start on port 8080 (or the PORT environment variable) and create a `books.db` SQLite database file.

## API Usage Examples

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

### List all books
```bash
curl http://localhost:8080/books
```

### Filter books by author
```bash
curl "http://localhost:8080/books?author=Alan%20A.%20A.%20Donovan"
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
    "title": "Updated Title",
    "author": "Updated Author",
    "year": 2023,
    "isbn": "0987654321"
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

## Running Tests

```bash
go test -v
```

The test suite includes 12 test cases covering:
- Health endpoint
- Book creation with validation
- Listing all books
- Getting a single book by ID
- Updating a book
- Deleting a book
- Author filtering
- Error handling (404, 400 responses)

## Project Structure

- `main.go` - Main application with REST API handlers
- `main_test.go` - Unit/integration tests
- `go.mod` - Go module dependencies
- `go.sum` - Go module checksums

## License

MIT
