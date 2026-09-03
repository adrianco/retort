# Book API REST Service

A REST API service for managing a book collection with CRUD operations, implemented in Go with SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation (title and author are required)
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
- SQLite3 database

## Setup

1. Make sure you have Go installed on your system
2. Clone or download this repository
3. Navigate to the project directory
4. Run `go mod tidy` to install dependencies

## Running the Application

```bash
go run main.go
```

The server will start on port 8080.

## Testing

You can test the API using curl or any HTTP client:

### Health Check
```bash
curl http://localhost:8080/health
```

### Create a Book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0-7432-7356-5"}'
```

### List All Books
```bash
curl http://localhost:8080/books
```

### List Books by Author
```bash
curl http://localhost:8080/books?author=Fitzgerald
```

### Get a Specific Book
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

## Database

The application uses SQLite database stored in `books.db` file in the project directory. The database is automatically created when the application starts.

## Testing

The application includes unit tests. Run them with:

```bash
go test -v
```