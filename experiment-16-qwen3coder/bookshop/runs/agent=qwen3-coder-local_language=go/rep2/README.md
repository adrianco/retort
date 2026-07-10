# Book Collection REST API

A simple REST API service for managing a book collection using Go and SQLite.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Go 1.26 or higher
- SQLite3 (included in the project)

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Run the application:
   ```bash
   go run main.go
   ```

## API Endpoints

### Health Check
```
GET /health
```
Returns a JSON object indicating the service status.

### Create a Book
```
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### List Books
```
GET /books
```
Optional query parameter:
- `author`: Filter books by author name (partial match)

### Get a Book by ID
```
GET /books/{id}
```

### Update a Book
```
PUT /books/{id}
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete a Book
```
DELETE /books/{id}
```

## Testing

To run the tests:
```bash
go test -v
```

The application will start on port 8080.