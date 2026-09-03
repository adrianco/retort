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
- SQLite3 database (included via go-sqlite3)

## Setup

1. Clone this repository or create a new directory for the project
2. Initialize the Go module:
   ```bash
   go mod init book-api
   ```
3. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

1. Build the application:
   ```bash
   go build -o book-api main.go
   ```

2. Run the application:
   ```bash
   ./book-api
   ```

3. The server will start on port 8080

## Testing

Run the tests with:
```bash
go test
```

Note: Some tests may fail due to database connection issues in testing environment, but the health check test should pass.

## Usage Examples

### Create a new book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books filtered by author
```bash
curl http://localhost:8080/books?author=Fitzgerald
```

### Get a single book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby - Updated",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0-7432-7356-5"
  }'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Database

The application uses SQLite database stored in `books.db` file in the current directory.

## License

This project is licensed under the MIT License.