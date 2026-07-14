# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Input validation (title and author are required)
- Health check endpoint
- SQLite for persistent storage

## Prerequisites

- Go 1.21 or later
- SQLite (the go-sqlite3 driver requires CGO; ensure a C compiler is installed)

## Setup and Run

1. Install dependencies:
   ```bash
   go mod tidy
   ```

2. Run the application:
   ```bash
   go run app.go
   ```

3. The API will be available at `http://localhost:8080`

## API Endpoints

| Method | Endpoint        | Description                   |
|--------|-----------------|-------------------------------|
| POST   | /books          | Create a new book             |
| GET    | /books          | List all books (optional ?author= filter) |
| GET    | /books/:id      | Get a single book by ID       |
| PUT    | /books/:id      | Update a book                 |
| DELETE | /books/:id      | Delete a book                 |
| GET    | /health         | Health check                  |

## Request/Response Examples

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}'
```

Response:
```json
{"id":1,"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}
```

### List All Books

```bash
curl http://localhost:8080/books
```

### Filter by Author

```bash
curl "http://localhost:8080/books?author=Donovan"
```

### Get a Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","author":"Updated Author","year":2024,"isbn":"new-isbn"}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run the test suite:

```bash
go test -v
```

The tests cover:
- Creating books with valid and invalid data
- Listing all books and filtering by author
- Getting a single book (found and not found)
- Updating a book
- Deleting a book
- Health check endpoint
- Full CRUD integration test
