# Book API REST Service

A REST API service for managing a book collection with SQLite persistence.

## Features

- Create, read, update, and delete books
- Store data in SQLite database
- JSON responses with appropriate HTTP status codes
- Input validation (title and author required)
- Health check endpoint

## Features

- Create, read, update, and delete books
- Store data in SQLite database
- JSON responses with appropriate HTTP status codes
- Input validation (title and author required)
- Health check endpoint

## API Endpoints

### Health Check

`GET /health`

Returns a health status status

### Create Book
`POST /books`

Create a new book with required fields:
- title (string)
- author (string) 
- year (integer)
- isbn (string)

### Get All Books

`GET /books`

Get all books (supports filtering by author)

### Get Book by ID

`GET /books/{id}`

Get a single book by ID

### Update Book

`PUT /books/{id}`

Update a book by ID

### Delete Book

`DELETE /books/{id}`

Delete a book by ID

## Setup

1. Install Go (version 1.16 or higher)
2. Install sqlite3 (if not already installed)
3. Clone or copy this directory to your local machine
4. Install dependencies:
   ```bash
   go mod init book-api
   go mod tidy
   ```

## Running the Server

```bash
go run main.go handlers.go
```

## Testing

```bash
go test -v
```

## Testing

```bash
go test -v
```

## Example Usage

```bash
# Create a book
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
  -d '{"title": "Updated Book Title", "author": "Updated Author", "year": 1925, "isbn": "978-0743273565"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Database Schema

The application uses SQLite to store book data in a `books` table with the following schema:

```sql
CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL,
 author TEXT NOT NULL,
 year INTEGER,
 isbn TEXT UNIQUE
);
```

## Testing

Run tests:

```bash
go test -v
```