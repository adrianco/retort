# Book API REST Service

A RESTful API service for managing a book collection, built with Go and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update an existing book (partial updates supported)
- **DELETE /books/{id}** — Delete a book by ID
- **GET /health** — Health check endpoint

## Requirements

- Go 1.20 or later
- SQLite3 (the `go-sqlite3` driver requires CGO; ensure a C compiler is available)

## Setup and Run

1. Clone or navigate to the project directory:
   ```bash
   cd book-api
   ```

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Run the server:
   ```bash
   go run main.go
   ```

The server starts on port 8080 by default. Set the `PORT` environment variable to change it:
```bash
PORT=3000 go run main.go
```

Set the `DB_PATH` environment variable to change the SQLite database file location:
```bash
DB_PATH=/tmp/books.db go run main.go
```

## Usage Examples

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

### Update a book (partial update)
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Go Programming Language, 2nd Edition"}'
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

Run all tests with the database in-memory (using a temp file per test):
```bash
go test ./... -v
```

Run specific test packages:
```bash
go test ./handlers/ -v
```
