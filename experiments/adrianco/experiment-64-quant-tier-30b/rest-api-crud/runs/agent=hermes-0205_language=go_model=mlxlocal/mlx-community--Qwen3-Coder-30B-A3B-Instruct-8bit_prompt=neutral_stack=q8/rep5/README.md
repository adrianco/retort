# Book API Go Implementation

This is a complete REST API service for managing a book collection implemented in Go with SQLite database.

## Features

- RESTful API with standard CRUD operations
- SQLite database for persistent storage
- Input validation 
- JSON responses with appropriate HTTP status codes
- Comprehensive test coverage

## Endpoints

### Health Check
- `GET /health` - Check service health

### Books Management
- `POST /books` - Create a new book
- `GET /books` - Get all books (with optional author filter)
- `GET /books/{id}` - Get a specific book by ID
- `PUT /books/{id}` - Update a specific book by ID
- `DELETE /books/{id}` - Delete a specific book by ID

## Requirements

- Go 1.21 or higher
- SQLite3

## Setup

1. Ensure Go is installed on your system
2. Clone this repository
3. Run `go mod tidy` to install dependencies

## Build

```bash
go build -o book-api main.go
```

## Run

```bash
./book-api
```

The server will start on port 8080.

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby - Revised","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Filter books by author
```bash
curl "http://localhost:8080/books?author=Fitzgerald"
```

## Implementation Details

The implementation uses:
- Go's standard `net/http` package for HTTP handling
- `database/sql` with `github.com/mattn/go-sqlite3` for database operations
- SQLite database file `books.db` for data persistence
- Structured JSON responses for all endpoints
- Proper HTTP status codes for different scenarios
- Input validation for required fields (title and author)
- Error handling for database operations

## Testing

The application includes comprehensive tests that verify all API endpoints work correctly. The tests can be run with:

```bash
go test -v
```

## License

MIT