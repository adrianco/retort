# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.21 or later

## Setup

1. Clone or navigate to the project directory.

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Run the application:
   ```bash
   go run app.go
   ```

   The server will start on `http://localhost:8080`.

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Donovan+%26+Kernighan"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","year":2024}'
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

Run the test suite:
```bash
go test -v
```

The tests cover:
- Health check endpoint
- Creating books (valid and invalid input)
- Listing all books and filtering by author
- Getting a single book by ID
- Updating a book
- Deleting a book
- Empty list handling

## API Response Format

All responses are JSON. Successful responses return the appropriate HTTP status code:

| Operation | Method | Status Code |
|-----------|--------|-------------|
| Create    | POST   | 201 Created |
| Read      | GET    | 200 OK      |
| Update    | PUT    | 200 OK      |
| Delete    | DELETE | 200 OK      |
| Not Found | any    | 404 Not Found |
| Bad Request | any  | 400 Bad Request |
| Error     | any    | 500 Internal Server Error |

Error responses include an `"error"` field with a description.
