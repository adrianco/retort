# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation (title and author required)
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books` - Create a new book (title, author, year, isbn)
- `GET /books` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.21 or higher
- SQLite3 (included via go-sqlite3)

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Run `go mod tidy` to download dependencies
4. Run `go run main.go` to start the server

## Usage

The server will start on port 8080.

### Examples

Create a new book:
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

Get all books:
```bash
curl http://localhost:8080/books
```

Get books by author:
```bash
curl http://localhost:8080/books?author=Fitzgerald
```

Get a specific book:
```bash
curl http://localhost:8080/books/1
```

Update a book:
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1926,"isbn":"978-0-7432-7356-5"}'
```

Delete a book:
```bash
curl -X DELETE http://localhost:8080/books/1
```

Check health:
```bash
curl http://localhost:8080/health
```

## Testing

Run tests with:
```bash
go test -v
```

## Database

The application uses an SQLite database file called `books.db` in the current directory to persist data.