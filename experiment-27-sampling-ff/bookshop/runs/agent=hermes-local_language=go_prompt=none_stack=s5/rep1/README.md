# Book Collection REST API

A simple REST API service for managing a book collection, built with Go and SQLite.

## Features

- Create, read, update, and delete books
- Filter books by author via query parameter
- Input validation (title and author are required)
- SQLite database for persistent storage
- Health check endpoint

## Endpoints

| Method | Endpoint       | Description              |
|--------|----------------|--------------------------|
| GET    | /health        | Health check             |
| POST   | /books         | Create a new book        |
| GET    | /books         | List all books           |
| GET    | /books/{id}    | Get a book by ID         |
| PUT    | /books/{id}    | Update a book            |
| DELETE | /books/{id}    | Delete a book            |

### Create Book Request Body

```json
{
  "title": "The Go Programming Language",
  "author": "Donovan & Kernighan",
  "year": 2015,
  "isbn": "978-0134190440"
}
```

### List Books with Filter

```
GET /books?author=Donovan
```

## Setup and Run

### Prerequisites

- Go 1.21 or later
- No external dependencies beyond the standard library and a pure-Go SQLite driver

### Build

```bash
go build -o bookapi .
```

### Run

```bash
./bookapi
```

The server starts on port 8080 by default. Configure with environment variables:

- `PORT` - Port to listen on (default: 8080)
- `DB_PATH` - Path to the SQLite database file (default: books.db)

### Run Tests

```bash
go test -v ./...
```

### Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}'

# List all books
curl http://localhost:8080/books

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Go Programming Language, Second Edition"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1

# Health check
curl http://localhost:8080/health
```
