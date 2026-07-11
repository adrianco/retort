# Book API REST Service

A REST API service for managing a book collection built with Go, GORM, and SQLite.

## Features

- **CRUD operations** for books (Create, Read, Update, Delete)
- **Health check endpoint** for monitoring
- **Author filtering** when listing books
- **Input validation** for book creation and updates
- **SQLite database** for data persistence
- **Comprehensive tests** to verify functionality

## Installation

### Prerequisites

- Go 1.19 or higher
- SQLite3 (should be pre-installed on most systems)

### Setup

1. Clone or copy the source files to your project directory

2. Install dependencies:

```bash
go mod tidy
```

This will install:
- `gorm.io/gorm` - ORM for database operations
- `gorm.io/driver/sqlite` - SQLite driver for GORM
- `github.com/stretchr/testify` - Testing framework

## Usage

### Running the Server

```bash
go run .
```

The server will start on port 8080 by default.

### API Endpoints

#### Health Check
```
GET /health
```
Response:
```json
{"status": "healthy"}
```

#### List All Books
```
GET /books
```
Optional query parameter:
- `?author=Author Name` - Filter books by author

Response:
```json
{
  "books": [
    {
      "id": 1,
      "title": "Book Title",
      "author": "Author Name",
      "year": 2023,
      "isbn": "978-1234567890",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

#### Get Single Book
```
GET /books/{id}
```

#### Create Book
```
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "978-1234567890"
}
```
Response: `201 Created`

#### Update Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Author Name",
  "year": 2023,
  "isbn": "978-1234567890"
}
```
Response: `200 OK`

#### Delete Book
```
DELETE /books/{id}
```
Response: `204 No Content`

## Input Validation

The API validates the following:
- **Title**: Required, cannot be empty
- **Author**: Required, cannot be empty
- **Year**: Required, must be a valid year (> 0)
- **ISBN**: Required, must be unique

## Running Tests

Run all tests:
```bash
go test -v
```

Run tests with coverage:
```bash
go test -v -coverprofile=coverage.out
go tool cover -html=coverage.out
```

## Project Structure

```
.
├── main.go           # Application entry point
├── server.go         # Main application logic and handlers
├── server_test.go    # Test suite
├── go.mod            # Go module definition
├── go.sum            # Go dependencies checksum
└── README.md         # This file
```

## Error Responses

The API returns appropriate HTTP status codes and JSON error messages:

| Status Code | Description |
|-------------|-------------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 409 | Conflict (duplicate ISBN) |
| 500 | Internal Server Error |

Example error response:
```json
{"error": "Book not found"}
```

## License

MIT
