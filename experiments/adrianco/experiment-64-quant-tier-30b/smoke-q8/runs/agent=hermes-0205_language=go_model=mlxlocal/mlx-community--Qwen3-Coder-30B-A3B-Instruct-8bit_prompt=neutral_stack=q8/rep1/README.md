# Book API Service

A REST API service for managing a book collection implemented in Go with SQLite database.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint
- Input validation
- JSON responses with appropriate HTTP status codes

## Endpoints

- `POST /books` - Create a new book
- `GET /books` - List all books (supports `?author=` filter)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book
- `GET /health` - Health check

## Requirements

- Go 1.26 or higher
- SQLite3

## Setup

1. Clone this repository
2. Navigate to the project directory
3. Install dependencies: `go mod tidy`

## Running the Application

```bash
go run main.go
```

The server will start on port 8080 by default. You can override the port by setting the `PORT` environment variable:

```bash
PORT=3000 go run main.go
```

## Testing

Run the tests with:

```bash
go test -v
```

## Example Usage

### Create a book
```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell","year":1948,"isbn":"978-0-452-28423-4"}'
```

### Get all books
```bash
curl http://localhost:8080/books
```

### Get books by author
```bash
curl http://localhost:8080/books?author=Orwell
```

### Get a specific book
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1948,"isbn":"978-0-452-28423-4"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```