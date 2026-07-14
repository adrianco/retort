# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** - Create a new book (title, author, year, isbn)
- **GET /books** - List all books (supports `?author=` filter)
- **GET /books/{id}** - Get a single book by ID
- **PUT /books/{id}** - Update a book
- **DELETE /books/{id}** - Delete a book
- **GET /health** - Health check endpoint

## Prerequisites

- Go 1.21 or later

## Setup and Run

1. Clone or navigate to the project directory.

2. Download dependencies:
   ```bash
   go mod tidy
   ```

3. Run the application:
   ```bash
   go run app.go
   ```

4. The API will be available at `http://localhost:8080`

## API Usage Examples

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List All Books
```bash
curl http://localhost:8080/books
```

### List Books by Author
```bash
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a Book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title","year":2024}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check
```bash
curl http://localhost:8080/health
```

## Testing

Run all tests:
```bash
go test -v
```

Run tests with coverage:
```bash
go test -v -cover
```

## Data Validation

- `title` is required and cannot be empty
- `author` is required and cannot be empty
- `year` and `isbn` are optional

## Database

Data is stored in an SQLite database file (`books.db`) in the project directory. The database is automatically created on first run.
