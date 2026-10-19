# Book API - Go REST Service

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (support `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Setup

1. Make sure you have Go 1.21+ installed
2. Clone or navigate to the project directory
3. Download dependencies:

```bash
go mod tidy
```

## Running

```bash
go run main.go
```

The server will start on `http://localhost:8080`.

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Alan Donovan", "year": 2015, "isbn": "978-0134190440"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=Alan Donovan"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language (2nd Edition)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Running Tests

```bash
go test -v
```

## Data Storage

Books are stored in a local SQLite database file (`books.db`) in the project directory.
