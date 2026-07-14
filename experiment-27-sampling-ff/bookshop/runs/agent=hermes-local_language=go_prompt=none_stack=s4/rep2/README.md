# Book API - REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (with optional `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Requirements

- Go 1.21 or later
- SQLite3 development libraries

## Setup and Run

1. Install dependencies:

```bash
go mod tidy
```

2. Run the application:

```bash
go run app.go
```

The API will be available at `http://localhost:8080`

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
curl "http://localhost:8080/books?author=F.+Scott+Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated Edition)"}'
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

## Input Validation

- `title` and `author` are required fields for creating a book
- Empty or whitespace-only values for title and author will return a 400 Bad Request error
