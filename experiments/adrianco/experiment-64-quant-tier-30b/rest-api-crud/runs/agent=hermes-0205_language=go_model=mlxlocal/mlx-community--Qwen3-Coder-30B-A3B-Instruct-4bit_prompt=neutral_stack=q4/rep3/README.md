# Book API REST Service

A simple REST API service for managing a book collection written in Go.

## Features

- Create new books (POST /books)
- Get all books (GET /books)
- Get a single book by ID (GET /books/{id})
- Update a book (PUT /books/{id})
- Delete a book (DELETE /books/{id})
- Health check endpoint (GET /health)

## Setup

1. Make sure you have Go installed (version 1.16+)
2. Clone or download this project
3. Navigate to the project directory
4. Install dependencies:

```bash
go mod tidy
```

5. Build the project:

```bash
go build main.go
```

6. Run the application:

```bash
./main
```

The server will start on port 8080.

## API Endpoints

### Health Check
- GET /health - Check if service is running

### Book Operations
- POST /books - Create a new book (requires title and author)
- GET /books - List all books (supports ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book

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

Get a specific book:
```bash
curl http://localhost:8080/books/1
```

Update a book:
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "author": "Updated Author", "year": 2023, "isbn": "1234567890"}'
```

Delete a book:
```bash
curl -X DELETE http://localhost:8080/books/1
```