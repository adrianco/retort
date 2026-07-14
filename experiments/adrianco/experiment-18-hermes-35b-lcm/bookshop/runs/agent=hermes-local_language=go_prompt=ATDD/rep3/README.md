# Book API REST Service

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (support `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- Language: Go
- Framework: gorilla/mux
- Database: SQLite (via mattn/go-sqlite3)
- JSON responses with appropriate HTTP status codes
- Input validation (title and author are required)

## Prerequisites

- Go 1.21 or later

## Setup and Run

1. Install dependencies:

   ```bash
   go mod tidy
   ```

2. Run the server:

   ```bash
   go run main.go
   ```

   The server starts on port 8080.

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Way","author":"Jane Smith","year":2024,"isbn":"978-0-00-000001"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Jane+Smith"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Jane Smith","year":2025,"isbn":"new-isbn"}'
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

Run all tests (unit + acceptance):

```bash
go test ./... -v
```

Run acceptance tests only:

```bash
go test -run Acceptance -v
```

Run with coverage:

```bash
go test ./... -cover
```

## Validation

- `title` is required — returns 400 if empty
- `author` is required — returns 400 if empty
