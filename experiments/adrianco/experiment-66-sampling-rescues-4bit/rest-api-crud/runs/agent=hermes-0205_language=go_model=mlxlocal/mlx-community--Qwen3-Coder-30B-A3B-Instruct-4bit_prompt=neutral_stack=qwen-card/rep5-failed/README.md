# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features

- REST API endpoints for managing books (create, read, update, delete)
- SQLite database storage for persistence
- Health check endpoint
- Input validation

## Requirements

- Go 1.16+ installed

## Setup Instructions

1. Clone this repository or copy the files to your local directory
2. Install dependencies:
   ```
   go mod tidy
   ```

3. Run the server:
   ```
   go run main.go
   ```

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /books` - List all books (supports ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `POST /books` - Create a new book (requires title and author)
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

## Example Usage

### Create a book:
```bash
curl -X POST http://localhost:8080/books \
-H "Content-Type: application/json" \
-d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
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
-d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'
```

### Delete a book:
```bash
curl -X DELETE http://localhost:8080/books/1
```

## Testing

Run tests:
```bash
go test -v
```

## Database

The application uses SQLite for data persistence. All data is stored in a file called `books.db` in the current directory.

## Building

To build a standalone executable:
```bash
go build main.go
```

This will create an executable named `main` (or `main.exe` on Windows).