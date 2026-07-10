# Book API

A REST API service for managing a book collection.

## Features

- POST /books — Create a new book (title, author, year, isbn)
- GET /books — List all books (support ?author= filter)
- GET /books/{id} — Get a single book by ID
- PUT /books/{id} — Update a book
- DELETE /books/{id} — Delete a book
- GET /health — Health check endpoint

## Requirements

- Go 1.16+
- SQLite database

## Setup

1. Install dependencies:
   ```
   go mod init book-api
   go get github.com/mattn/go-sqlite3
   ```

2. Run the application:
   ```
   go run main.go
   ```

3. The server will start on `http://localhost:8080`

## Usage Examples

### Create a book
```bash
curl -X POST http://localhost:8080/books   -H "Content-Type: application/json"   -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### List all books
```bash
curl http://localhost:8080/books
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1   -H "Content-Type: application/json"   -d '{
    "title": "The Great Gatsby - Revised Edition",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```
