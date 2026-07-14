# Book Collection REST API

A simple REST API service for managing a book collection, implemented in Go with SQLite storage.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Go 1.21 or later
- SQLite3 (included in the sqlite3 driver)

## Setup

1. Install dependencies:
   ```bash
   go mod tidy
   ```

2. Build the application:
   ```bash
   go build -o bookapi
   ```

3. Run the application:
   ```bash
   ./bookapi
   ```

4. The server will start on `http://localhost:8080`

## API Endpoints

### Create a new book
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

### List all books
```
GET /books
```

### List books by author
```
GET /books?author=Fitzgerald
```

### Get a single book
```
GET /books/1
```

### Update a book
```
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby - Revised Edition",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete a book
```
DELETE /books/1
```

### Health check
```
GET /health
```

## Implementation Details

This implementation includes:

1. **SQLite Database Storage**: All data is persisted in a local SQLite database file (`books.db`)
2. **Complete CRUD Operations**: Create, Read, Update, and Delete books
3. **Input Validation**: Ensures required fields (title and author) are provided
4. **HTTP Status Codes**: Appropriate responses with correct HTTP status codes
5. **JSON Responses**: All endpoints return data in JSON format
6. **Filtering**: GET /books supports filtering by author using query parameters
7. **Health Check**: Dedicated endpoint for monitoring service status

## Testing

The application has been tested to ensure:

- All CRUD operations work correctly
- Input validation properly rejects invalid data
- HTTP status codes are returned appropriately
- Database persistence works correctly
- Error handling works for edge cases

## Usage Examples

### Creating a book:
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0-452-28423-4"
  }'
```

### Listing all books:
```bash
curl http://localhost:8080/books
```

### Listing books by author:
```bash
curl http://localhost:8080/books?author=Orwell
```

### Getting a specific book:
```bash
curl http://localhost:8080/books/1
```

### Updating a book:
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984 - Revised Edition",
    "author": "George Orwell",
    "year": 1948,
    "isbn": "978-0-452-28423-4"
  }'
```

### Deleting a book:
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check:
```bash
curl http://localhost:8080/health
```