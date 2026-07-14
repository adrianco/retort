# Book API REST Service

A REST API service for managing a book collection built with Go, Gin, and SQLite.

## Features

- **Full CRUD Operations**: Create, Read, Update, and Delete books
- **Author Filter**: Filter books by author
- **Input Validation**: Ensures title and author fields are provided
- **SQLite Storage**: Persistent local storage for your book collection
- **Health Check**: Basic health monitoring endpoint

## Installation

### Prerequisites

- Go 1.21 or higher
- SQLite development headers (for CGO)

### Setup

1. Clone this repository or navigate to the project directory

2. Install dependencies:
```bash
go mod tidy
```

3. Build the application:
```bash
go build -o bookapi
```

## Running the Application

### Development Mode

```bash
go run app.go
```

### Production Mode

```bash
./bookapi
```

By default, the server will start on port 8080. You can change the port by setting the `PORT` environment variable:

```bash
PORT=3000 ./bookapi
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns the current health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-07-12T03:28:27Z",
  "database": "connected"
}
```

### List All Books
```
GET /api/books
```
Returns a list of all books.

With optional author filter:
```
GET /api/books?author=John+Doe
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }
]
```

### Get a Book by ID
```
GET /api/books/{id}
```

**Response (success):**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Response (not found):**
```json
{
  "error": "Book not found"
}
```

### Create a Book
```
POST /api/books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Response (success):**
```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

**Response (validation error):**
```json
{
  "error": "Title is required"
}
```

### Update a Book
```
PUT /api/books/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "year": 2024,
  "isbn": "123-4567890123"
}
```

### Delete a Book
```
DELETE /api/books/{id}
```

## Testing

Run the test suite:
```bash
go test -v
```

The test suite includes:
- Health check endpoint tests
- Book creation with validation
- Book listing (all and filtered by author)
- Book retrieval by ID
- Book update
- Book deletion
- Error handling tests

## Project Structure

```
├── app.go         # Main application with all API endpoints
├── app_test.go    # Unit tests
├── go.mod         # Go module dependencies
├── go.sum         # Go dependencies checksum
└── README.md      # This file
```

## License

MIT License
