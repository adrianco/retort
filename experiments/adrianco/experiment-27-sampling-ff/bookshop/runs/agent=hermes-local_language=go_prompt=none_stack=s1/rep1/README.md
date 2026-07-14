# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite3 (the go-sqlite3 driver requires CGO)

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

## Testing

Run the unit tests:
```bash
go test -v
```

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
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a single book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Data Model

| Field  | Type   | Required | Description          |
|--------|--------|----------|----------------------|
| id     | int    | Auto     | Unique identifier    |
| title  | string | Yes      | Book title           |
| author | string | Yes      | Book author          |
| year   | int    | Yes      | Publication year     |
| isbn   | string | Yes      | ISBN number          |

## Validation

- `title` is required
- `author` is required
- `year` must be an integer
- `isbn` must be a string
