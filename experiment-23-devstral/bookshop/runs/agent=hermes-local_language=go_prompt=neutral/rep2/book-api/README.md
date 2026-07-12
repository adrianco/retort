# Book API REST Service

This is a REST API service for managing a book collection. It provides endpoints for creating, reading, updating, and deleting books, with filtering by author.

## Requirements
- Go 1.18 or later
- SQLite

## Installation

1. Install Go from https://golang.org/dl/ if you haven't already.
2. Set up a Go workspace with GOPATH.
3. Install the required dependencies:
   ```
   go mod tidy
   ```
4. Run the application:
   ```
   go run app.go
   ```

## API Endpoints

- **POST /books**: Create a new book
  - Request body: `{"title": "string", "author": "string", "year": number, "isbn": "string"}`
  - Returns: Created book with ID

- **GET /books**: List all books (optional filter by author)
  - Query parameter: `author` (optional)
  - Returns: Array of books

- **GET /books/{id}**: Get a single book by ID
  - Returns: Book object

- **PUT /books/{id}**: Update a book
  - Request body: Updated book fields
  - Returns: Updated book

- **DELETE /books/{id}**: Delete a book
  - Returns: No content

- **GET /health**: Health check endpoint
  - Returns: `{"status": "healthy"}`

## Testing

The application includes a basic test suite. Run the tests with:
```
go test -v
```

## Database

The application uses SQLite for data storage. The database file (`books.db`) is created in the same directory as the application.

## Contributing

Feel free to submit issues or pull requests for improvements.
