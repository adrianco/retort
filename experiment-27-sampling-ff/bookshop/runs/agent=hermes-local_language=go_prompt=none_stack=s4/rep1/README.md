# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Prerequisites

- Go 1.21 or later
- SQLite (the `go-sqlite3` driver requires CGO)

## Setup

1. Clone or navigate to the project directory.

2. Download dependencies:

   ```bash
   go mod tidy
   ```

3. Ensure CGO is enabled (required for go-sqlite3):

   ```bash
   export CGO_ENABLED=1
   ```

## Running the Server

```bash
go run app.go
```

The API will be available at `http://localhost:8080`.

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

### List books by author

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
  -d '{"title":"Updated Title"}'
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
- Creating books (valid and invalid input)
- Listing all books and filtering by author
- Getting a single book (found and not found)
- Updating a book (partial and full updates)
- Deleting a book (found and not found)
- Invalid book ID handling
