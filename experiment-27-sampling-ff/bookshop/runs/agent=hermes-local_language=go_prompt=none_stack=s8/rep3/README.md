# Book API REST Service

A REST API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite (the `github.com/mattn/go-sqlite3` driver uses CGO, so you need a C compiler)

## Setup and Run

1. **Install dependencies:**
   ```bash
   go mod tidy
   ```

2. **Run the server:**
   ```bash
   go run app.go
   ```

3. The API will be available at `http://localhost:8080`

## API Examples

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

### Filter by author
```bash
curl "http://localhost:8080/books?author=Alan+Donovan"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Author Name"}'
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

The tests cover:
- Health check endpoint
- Create, read, update, delete (CRUD) operations
- Input validation (title and author required)
- Author filtering
- Error handling (not found, invalid JSON, duplicate ISBN)
- Full CRUD lifecycle

## Data Storage

Books are stored in an SQLite database (`books.db`) created automatically on server start. The `title` and `isbn` fields are required (non-empty). The `isbn` field is unique across all books.
