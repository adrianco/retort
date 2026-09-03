# Book API REST Service

A REST API service for managing a book collection built with Go.

## Features

- Create, read, update, and delete books
- Filter books by author
- Health check endpoint

## Requirements

- Go 1.16+
- SQLite3 database (embedded)

## Installation

1. Clone or download this repository
2. Navigate to the directory containing the code
3. Build the project with: `go build -o book-api main.go`

## Usage

1. Run the server: `./book-api`
2. The server will start on port 8080

## API Endpoints

### Health Check
- `GET /health`

### Book Management
- `POST /books` - Create a new book (requires title and author)
- `GET /books` - List all books (supports filtering by author)
- `GET /books/{id}` - Get a single book by ID
- `PUT /books/{id}` - Update a book
- `DELETE /books/{id}` - Delete a book

### Example Usage

```bash
# Create a new book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'

# Get all books
curl http://localhost:8080/books

# Get a specific book by ID
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925, "isbn": "978-0743273565"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Database

The application uses an SQLite database stored in `books.db` file in the current directory.

## Testing

Tests can be run with:

```bash
go test -v
```

## License

MIT