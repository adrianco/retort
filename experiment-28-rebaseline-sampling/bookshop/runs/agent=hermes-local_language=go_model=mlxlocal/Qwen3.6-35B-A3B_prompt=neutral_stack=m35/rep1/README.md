# Book Collection REST API

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **CRUD Operations**: Create, Read, Update, and Delete books
- **Filtering**: List books filtered by author using the `?author=` query parameter
- **Input Validation**: Title and author are required fields
- **Health Check**: Simple endpoint to verify the service is running
- **SQLite Storage**: Embedded database for persistent storage

## API Endpoints

| Method | Endpoint         | Description                  |
|--------|------------------|------------------------------|
| GET    | /health          | Health check                 |
| POST   | /books           | Create a new book            |
| GET    | /books           | List all books               |
| GET    | /books/:id       | Get a single book by ID      |
| PUT    | /books/:id       | Update a book                |
| DELETE | /books/:id       | Delete a book                |

### Book Schema

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Create Book Request

```json
{
  "title": "Book Title",
  "author": "Author Name",
  "year": 2024,
  "isbn": "978-0000000000"
}
```

## Setup and Run

### Prerequisites

- Go 1.26 or later

### Installation

1. Initialize the Go module:

```bash
go mod tidy
```

2. Run the application:

```bash
go run app.go
```

The server will start on `http://localhost:8080`.

## Testing

Run all tests:

```bash
go test -v
```

## Usage Examples

### Create a book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List all books

```bash
curl http://localhost:8080/books
```

### List books by author

```bash
curl "http://localhost:8080/books?author=F. Scott Fitzgerald"
```

### Get a book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```
