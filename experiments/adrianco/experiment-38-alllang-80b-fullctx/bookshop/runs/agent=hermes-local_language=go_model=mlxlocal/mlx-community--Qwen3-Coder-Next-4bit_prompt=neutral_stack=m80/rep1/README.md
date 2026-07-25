# Book API REST Service

A REST API service for managing a book collection built with Go, using SQLite for data storage.

## Features

- Create, read, update, and delete books
- List all books with optional author filter
- Health check endpoint
- Input validation
- SQLite database persistence

## Installation

### Prerequisites

- Go 1.21 or higher
- SQLite3 development libraries

### Setup

1. Clone or navigate to the project directory

2. Install dependencies:
```bash
go mod download
```

## Running the Server

### Default (port 8080, books.db in current directory)

```bash
go run main.go
```

### With custom configuration

```bash
# Set custom port
PORT=3000 go run main.go

# Set custom database path
BOOK_DB_PATH=/path/to/database.db go run main.go

# Set both
PORT=3000 BOOK_DB_PATH=/path/to/database.db go run main.go
```

## API Endpoints

### Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### List Books
```
GET /books
GET /books?author=Author%20Name
```

### Get Book by ID
```
GET /books/{id}
```

### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "1234567890"
}
```

### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "1234567890"
}
```

### Delete Book
```
DELETE /books/{id}
```

## Testing

Run all tests:
```bash
go test -v
```

Run tests with coverage:
```bash
go test -v -coverprofile=coverage.out
go tool cover -html=coverage.out
```

Run specific test:
```bash
go test -v -run TestCreateBook
```

## Project Structure

```
.
├── main.go          # Main application with HTTP server and routes
├── database.go      # Database layer and CRUD operations
├── main_test.go     # Unit and integration tests
├── go.mod           # Go module dependencies
├── go.sum           # Go module checksums
└── README.md        # This file
```

## Error Responses

The API returns appropriate HTTP status codes:

- `200 OK` - Successful GET, PUT requests
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Validation errors or invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server errors

Error response format:
```json
{
  "error": "Error message describing what went wrong"
}
```

## License

MIT
