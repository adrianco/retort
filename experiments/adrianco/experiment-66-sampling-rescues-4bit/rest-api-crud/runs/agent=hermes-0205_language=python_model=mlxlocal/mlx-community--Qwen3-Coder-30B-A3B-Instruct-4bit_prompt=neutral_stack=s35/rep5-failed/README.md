# Book API REST Service

A REST API service for managing a book collection built with Go and SQLite.

## Features
- Create, read, update, and delete books (CRUD operations)
- Filter books by author using query parameter
- Health check endpoint
- SQLite database storage

## API Endpoints
- `GET /health` - Health check endpoint
- `GET /books` - List all books (supports filtering by author)
- `GET /books/:id` - Get a single book by ID
- `POST /books` - Create a new book
- `PUT /books/:id` - Update an existing book
- `DELETE /books/:id` - Delete a book

## Installation
1. Clone the repository
2. Install Go dependencies:
   ```bash
   go mod tidy
   ```
3. Build the application:
   ```bash
   go build -o book-api main.go
   ```

## Usage
1. Run the server:
   ```bash
   ./book-api
   ```
2. The API will be available at http://localhost:8080

## Testing
You can test the API using curl or any HTTP client:

```bash
# Health check
curl http://localhost:8080/health

# Get all books
curl http://localhost:8080/books

# Create a new book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Donovan & Kernighan", "year": 2015, "isbn": "0134076854"}'

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "The Go Programming Language", "author": "Donovan & Kernighan", "year": 2015, "isbn": "0134076854"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Database
The application uses SQLite for data persistence. The database file `book.db` will be created in the working directory when the application starts.

## Testing
The service includes basic unit tests and integration tests that verify:
- Health check endpoint works correctly
- Book creation and retrieval works
- Update and delete operations work
- Error handling for invalid requests