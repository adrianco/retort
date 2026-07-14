# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- Language: Go 1.21+
- Framework: Gin (web framework)
- Database: SQLite (embedded, no server required)
- All responses are in JSON format with appropriate HTTP status codes

## Prerequisites

- Go 1.21 or later
- GCC (required for CGO, used by go-sqlite3)

## Setup and Run

1. Clone or navigate to the project directory:
   ```bash
   cd book-api
   ```

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Run the application:
   ```bash
   go run app.go
   ```

4. The API will be available at `http://localhost:8080`

   To use a different port, set the `PORT` environment variable:
   ```bash
   PORT=3000 go run app.go
   ```

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Alan+Donovan"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language (Updated)","author":"Alan Donovan","year":2022,"isbn":"978-0134190440"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Testing

Run all tests:
```bash
go test -v
```

The test suite covers:
- Health check endpoint
- Create book (success and validation failures)
- List books (empty, all, filtered by author)
- Get book by ID (found and not found)
- Update book (success, validation failures, not found)
- Delete book (success, not found)
- Invalid JSON handling

## Project Structure

```
app.go          - Main application with all API endpoints and database logic
app_test.go     - Comprehensive test suite for all endpoints
go.mod          - Go module definition and dependencies
README.md       - This file
```

## Validation Rules

- `title` is required (cannot be empty)
- `author` is required (cannot be empty)
- `year` and `isbn` are optional but must be valid types if provided
