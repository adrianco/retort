# Book API - REST Service

A REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite (the `go-sqlite3` driver requires CGO; ensure a C compiler is installed)

## Setup and Run

```bash
# Install dependencies
go mod tidy

# Run the application
go run app.go
```

The API will be available at `http://localhost:8080`.

You can set a custom port via the `PORT` environment variable:

```bash
PORT=3000 go run app.go
```

## Testing

Run the test suite:

```bash
go test -v ./...
```

## API Examples

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
curl "http://localhost:8080/books?author=Donovan%20%26%20Kernighan"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Response Format

All responses are JSON. Successful operations return the appropriate HTTP status code:

| Operation | Status Code |
|-----------|-------------|
| Create    | 201 Created |
| Read      | 200 OK      |
| Update    | 200 OK      |
| Delete    | 200 OK      |
| Not Found | 404         |
| Bad Request | 400       |
| Error     | 500         |

Error responses include an `"error"` field with a description.
