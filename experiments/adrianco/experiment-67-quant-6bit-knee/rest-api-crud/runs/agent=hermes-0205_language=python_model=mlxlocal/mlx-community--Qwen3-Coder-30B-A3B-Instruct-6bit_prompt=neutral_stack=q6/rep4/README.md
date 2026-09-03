# Book API REST Service

A REST API service for managing a book collection with CRUD operations.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes
- SQLite database storage

## Endpoints

- `POST /books/` - Create a new book (title, author, year, isbn)
- `GET /books/` - List all books (support ?author= filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.21 or higher

## Setup

1. Clone or download this repository
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   go mod tidy
   ```

## Running the Application

```bash
go run main.go
```

The server will start on port 8080.

## Testing

The API can be tested with curl commands or any HTTP client:

### Health Check
```bash
curl http://localhost:8080/health
```

### Create a Book
```bash
curl -X POST http://localhost:8080/books/ \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Get All Books
```bash
curl http://localhost:8080/books/
```

### Get Books by Author
```bash
curl "http://localhost:8080/books/?author=Fitzgerald"
```

### Get a Single Book
```bash
curl http://localhost:8080/books/1
```

### Update a Book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### Delete a Book
```bash
curl -X DELETE http://localhost:8080/books/1
```