# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Endpoints

| Method | Endpoint         | Description                          |
|--------|------------------|--------------------------------------|
| POST   | /books           | Create a new book                    |
| GET    | /books           | List all books (optional ?author=)   |
| GET    | /books/:id       | Get a single book by ID              |
| PUT    | /books/:id       | Update a book                        |
| DELETE | /books/:id       | Delete a book                        |
| GET    | /health          | Health check                         |

## Setup and Run

### Prerequisites
- Go 1.21 or later
- GCC (required by go-sqlite3)

### Installation

```bash
go mod tidy
```

This will download all dependencies (Gin web framework and SQLite3 driver).

### Running the Server

```bash
go run app.go
```

The server starts on port 8080 by default. Set the `PORT` environment variable to change it:

```bash
PORT=3000 go run app.go
```

## Usage Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=Alan+Donovan"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language (2nd Edition)","year":2022}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
# Response: {"status":"ok"}
```

## Testing

Run all tests with verbose output:

```bash
go test -v
```

The test suite includes 12 tests covering:
- Health check endpoint
- Create book (success and validation)
- List all books and filter by author
- Get single book and not-found case
- Update book (success, partial update, not-found)
- Delete book (success, not-found)
- Empty list handling

## Data Model

Books are stored in SQLite with the following schema:

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
```

## Validation

- `title` and `author` are required fields for creating a book
- Missing or empty title/author returns HTTP 400 Bad Request with an error message
