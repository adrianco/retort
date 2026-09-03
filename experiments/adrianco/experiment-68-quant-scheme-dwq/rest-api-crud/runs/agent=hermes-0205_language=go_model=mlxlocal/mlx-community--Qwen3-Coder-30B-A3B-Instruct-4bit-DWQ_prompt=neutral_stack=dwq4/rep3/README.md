# Book API REST Service

A REST API for managing a book collection implemented in Go with SQLite database.

## Features

- POST /books - Create a new book (title, author, year, isbn)
- GET /books - List all books (support ?author= filter)
- GET /books/{id} - Get a single book by ID
- PUT /books/{id} - Update a book
- DELETE /books/{id} - Delete a book
- GET /health - Health check endpoint

## Requirements

- Go 1.16 or later
- SQLite database (embedded)

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   go mod tidy
   ```

3. Run the application:
   ```bash
   go run main.go
   ```

The server will start on port 8080 by default. You can override the port by setting the `PORT` environment variable.

## API Endpoints

### Health Check
```bash
GET /health
```
Response: `{"status":"healthy"}`

### Create Book
```bash
POST /books
Content-Type: application/json

{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Get All Books
```bash
GET /books
```
Response: Array of all books

### Get Books by Author
```bash
GET /books?author=Fitzgerald
```
Response: Array of books by the specified author

### Get Single Book
```bash
GET /books/1
```
Response: Single book object

### Update Book
```bash
PUT /books/1
Content-Type: application/json

{
  "title": "The Great Gatsby - Revised Edition",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0-7432-7356-5"
}
```

### Delete Book
```bash
DELETE /books/1
```

## Testing

Run tests with:
```bash
go test -v
```

## Database

The application uses an embedded SQLite database stored in `books.db` file in the working directory.

## License

MIT