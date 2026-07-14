# Book Collection REST API

A REST API service for managing a book collection, built in Go with SQLite.

## Endpoints

### POST /books
Create a new book.

Request body (JSON):
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

Validation: title, author, and year are required. ISBN must be unique.

Response: 201 Created with the created book, or 400 Bad Request with validation errors.

### GET /books
List all books.

Optional query parameter: `?author=Author Name` to filter by author.

Response: 200 OK with an array of books.

### GET /books/{id}
Get a single book by its ID.

Response: 200 OK with the book, or 404 Not Found.

### PUT /books/{id}
Update an existing book.

Request body (JSON):
```json
{
  "title": "1984 (Updated Edition)",
  "author": "George Orwell",
  "year": 1949,
  "isbn": "978-0451524935"
}
```

Response: 200 OK with the updated book, or 404 Not Found.

### DELETE /books/{id}
Delete a book by its ID.

Response: 204 No Content.

### GET /health
Health check endpoint.

Response: 200 OK with `{"status": "healthy"}`.

## Requirements

- Go 1.21+

## Setup and Run

1. Install Go from https://golang.org/dl/

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Build:
   ```bash
   go build -o book-api
   ```

4. Run:
   ```bash
   ./book-api
   ```

The server starts on port 8080.

## API Examples

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=George+Orwell"

# Get a book by ID
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"1984 (Updated)","author":"George Orwell","year":1949,"isbn":"978-0451524935"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```

## Running Tests

```bash
go test -v ./...
```

All tests use the in-memory SQLite database, so no external database is needed.
