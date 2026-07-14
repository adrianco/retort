# Book API

A simple REST API for managing a book collection.

## Features

- Create books (POST /books)
- List all books (GET /books) with optional author filter
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Requirements

- Go 1.19+
- SQLite

## Setup

1. Clone or download this repository
2. Navigate to the project directory
3. Run `go mod tidy` to install dependencies
4. Run the application with `go run .`

## API Endpoints

### Health Check
GET /health

### Books
POST /books
GET /books
GET /books/{id}
PUT /books/{id}
DELETE /books/{id}

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```
