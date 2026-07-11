# Book Collection REST API

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (with optional `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update an existing book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Requirements

- Go 1.21+
- (SQLite is embedded via the `modernc.org/sqlite` pure-Go driver; no external DB installation needed)

## Setup and Run

```bash
# Navigate to the project directory
cd bookapi

# Download dependencies
go mod tidy

# Run the server
go run .

# The server starts on port 8080 (override with PORT env var)
PORT=3000 go run .
```

## API Examples

```bash
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

# Health check
curl http://localhost:8080/health
```

## Running Tests

```bash
go test ./... -v
```
