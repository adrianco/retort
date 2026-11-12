# Book Collection REST API

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST** `/books` — Create a new book (title, author, year, isbn)
- **GET** `/books` — List all books (supports `?author=` filter)
- **GET** `/books/{id}` — Get a single book by ID
- **PUT** `/books/{id}` — Update a book
- **DELETE** `/books/{id}` — Delete a book
- **GET** `/health` — Health check endpoint

## Requirements

- Go 1.21 or later
- SQLite (via `github.com/mattn/go-sqlite3` CGo dependency)

## Setup

```bash
# Download dependencies
go mod tidy

# Run the server
go run main.go
```

The server will start on `http://localhost:8080`.

## Running Tests

```bash
go test -v ./...
```

## API Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### List all books
```bash
curl http://localhost:8080/books
```

### List books by author
```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby (Revised)"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```
