# Book API REST Service

A REST API service for managing a book collection, built with Go and SQLite.

## API Endpoints

| Method | Endpoint          | Description                    |
|--------|-------------------|--------------------------------|
| GET    | /health           | Health check endpoint          |
| POST   | /books            | Create a new book              |
| GET    | /books            | List all books (optional `?author=` filter) |
| GET    | /books/{id}       | Get a single book by ID        |
| PUT    | /books/{id}       | Update a book                  |
| DELETE | /books/{id}       | Delete a book                  |

## Book Fields

- `title` (string, required)
- `author` (string, required)
- `year` (integer)
- `isbn` (string)

## Setup and Run

1. Ensure Go 1.21+ is installed.

2. Build:
   ```bash
   go build -o bookapi .
   ```

3. Run:
   ```bash
   ./bookapi
   ```

   The server listens on port 8080 by default. Override with the `PORT` environment variable.

   The SQLite database file defaults to `books.db` in the current directory. Override with the `BOOK_API_DB` environment variable.

## Example Usage

```bash
# Create a book
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'

# List all books
curl http://localhost:8080/books

# List books by author
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"

# Get a single book
curl http://localhost:8080/books/1

# Update a book
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'

# Delete a book
curl -X DELETE http://localhost:8080/books/1
```

## Running Tests

```bash
go test -v ./...
```
