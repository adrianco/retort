# Book API REST Service

A REST API service for managing a book collection, built in Go with SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- Language: Go 1.26
- Database: SQLite (embedded, via modernc.org/sqlite — pure Go, no CGO required)
- Input validation: title and author are required fields
- All responses are JSON with appropriate HTTP status codes

## Prerequisites

- Go 1.21 or later

## Setup and Run

```bash
# Clone or navigate to the project directory
cd book-api

# Download dependencies
go mod download

# Build the server
go build -o book-api-server .

# Run the server
./book-api-server
# Server starts on http://localhost:8080

# Or run directly:
go run main.go
```

## API Examples

```bash
# Health check
curl http://localhost:8080/health

# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Running Tests

```bash
go test ./... -v
```

Tests cover:
- Health check endpoint
- Book creation (valid and invalid input)
- Listing all books and filtering by author
- Getting a single book by ID
- Updating a book
- Deleting a book
- Full CRUD lifecycle
