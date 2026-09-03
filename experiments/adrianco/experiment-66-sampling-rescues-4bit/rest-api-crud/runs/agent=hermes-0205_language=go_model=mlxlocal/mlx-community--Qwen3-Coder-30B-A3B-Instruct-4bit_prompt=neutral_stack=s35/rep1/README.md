# Book API REST Service

A simple REST API service for managing a book collection built in Go.

## Features

- REST API with CRUD operations for books
- GET /health - Health check endpoint
- GET /books - List all books (with author filtering)
- GET /books/{id} - Get a single book by ID
- POST /books - Create new books with validation
- PUT /books/{id} - Update existing books
- DELETE /books/{id} - Delete books

## Requirements

- Go 1.19 or higher
- Gorilla mux library (will be installed automatically)

## Installation

1. Clone the repository or copy the code files to your local directory
2. Install dependencies:
   ```bash
   go mod tidy
   ```
3. Build the application:
   ```bash
   go build -o book-api main.go
   ```
4. Run the server:
   ```bash
   ./book-api
   ```

## API Endpoints

### Health Check
- `GET /health` - Returns health status

### Book Management
- `GET /books` - Get all books (supports ?author= filter)
- `GET /books/{id}` - Get a specific book by ID
- `POST /books` - Create a new book (JSON payload required)
- `PUT /books/{id}` - Update an existing book
- `DELETE /books/{id}` - Delete a book

### Example Usage

Create a new book:
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "9780743273502"}'
```

Get all books:
```bash
curl http://localhost:8080/books
```

Get books by author:
```bash
curl http://localhost:8080/books?author=F. Scott Fitzgerald
```

Get specific book:
```bash
curl http://localhost:8080/books/1
```

Update a book:
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "author": "Updated Author", "year": 1925, "isbn": "9780743273502"}'
```

Delete a book:
```bash
curl -X DELETE http://localhost:8080/books/1
```