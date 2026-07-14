# Book Collection REST API

A simple REST API service for managing a book collection built with Go and SQLite.

## Features

- POST /books - Create a new book
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Go 1.21 or higher
- SQLite (embedded database)

## Setup

1. Install dependencies:
   ```bash
   go mod tidy
   ```

2. Run the server:
   ```bash
   go run main.go
   ```

3. The server will start on port 8080 by default, or use the PORT environment variable.

## API Endpoints

### Create a new book
```bash
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### List all books
```bash
GET /books
```

### List books by author
```bash
GET /books?author=Fitzgerald
```

### Get a book by ID
```bash
GET /books/1
```

### Update a book
```bash
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete a book
```bash
DELETE /books/1
```

### Health check
```bash
GET /health
```

## Testing

Run the unit tests:
```bash
go test
```

## Data Storage

The application uses SQLite database stored in `books.db` file in the working directory.