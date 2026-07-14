# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book (supports partial updates)
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Technical Details

- Language: Go 1.26
- Framework: Gin (web framework)
- Database: SQLite (embedded, file-based)
- All responses are in JSON format with appropriate HTTP status codes

## Setup and Run Instructions

### Prerequisites

- Go 1.26 or later
- GCC (required for CGO, used by the SQLite driver)

### Installation

1. Clone or navigate to the project directory
2. Download dependencies:

```bash
go mod tidy
```

### Running the Server

```bash
go run app.go
```

The server will start on `http://localhost:8080`

### Running Tests

```bash
go test -v
```

## API Examples

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### List Books by Author

```bash
curl "http://localhost:8080/books?author=Alan%20Donovan"
```

### Get a Book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Validation Rules

- `title` is required when creating a book
- `author` is required when creating a book
- All fields are optional when updating (partial updates supported)
