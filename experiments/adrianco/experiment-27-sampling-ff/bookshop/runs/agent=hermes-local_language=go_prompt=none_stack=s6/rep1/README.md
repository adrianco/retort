# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.21 or later
- GCC (required for CGO, used by go-sqlite3)

## Setup and Run

1. Install Go dependencies:
   ```bash
   go mod tidy
   ```

2. Run the application:
   ```bash
   go run app.go
   ```

3. The API will be available at `http://localhost:8080`

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Orwell"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Updated Author","year":2020,"isbn":"111-1111111111"}'
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

## Technical Details

- **Framework**: Gin (Go web framework)
- **Database**: SQLite (embedded, no external server needed)
- **Data persistence**: Books are stored in `books.db` (file-based) or in-memory for tests
- **Validation**: Title and author are required fields for book creation
