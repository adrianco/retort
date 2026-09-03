# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Endpoints

- `GET /health` - Health check
- `GET /books` - List all books (supports filtering by author)
- `GET /books/{id}` - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/{id}` - Update an existing book
- `DELETE /books/{id}` - Delete a book

## Requirements

- Go 1.16+ installed
- SQLite database support

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Install dependencies:

```bash
go mod tidy
```

## Running the Application

```bash
go run main.go
```

The server will start on port 8080.

## Testing

Run tests with:

```bash
go test -v
```

## API Usage Examples

### Create a book:

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273502"}'
```

### Get all books:

```bash
curl http://localhost:8080/books
```

### Get a specific book:

```bash
curl http://localhost:8080/books/1
```

### Update a book:

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "author": "Updated Author", "year": 2023, "isbn": "1234567890"}'
```

### Delete a book:

```bash
curl -X DELETE http://http://localhost:8080/books/1
```

### Filter books by author:

```bash
curl "http://localhost:8080/books?author=F. Scott Fitzgerald"
```