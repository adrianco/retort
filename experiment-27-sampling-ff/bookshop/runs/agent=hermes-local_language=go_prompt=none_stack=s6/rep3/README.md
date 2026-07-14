# Book API REST Service

A REST API service for managing a book collection, built with Go, Gin, and SQLite.

## Features

- **POST /books** — Create a new book (title, author, year, isbn)
- **GET /books** — List all books (supports `?author=` filter)
- **GET /books/{id}** — Get a single book by ID
- **PUT /books/{id}** — Update a book
- **DELETE /books/{id}** — Delete a book
- **GET /health** — Health check endpoint

## Technical Details

- Language: Go 1.21+
- Framework: Gin (web framework)
- Database: SQLite (via go-sqlite3)
- All responses are JSON with appropriate HTTP status codes
- Input validation: title and author are required fields

## Setup and Run

1. Install dependencies:
   ```bash
   go mod tidy
   ```

2. Run the application:
   ```bash
   go run app.go
   ```

3. The API will be available at `http://localhost:8080`

## API Usage Examples

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
curl "http://localhost:8080/books?author=F.%20Scott%20Fitzgerald"
```

### Get a book by ID
```bash
curl http://localhost:8080/books/1
```

### Update a book
```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### Delete a book
```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check
```bash
curl http://localhost:8080/health
```

## Testing

Run the unit and integration tests:
```bash
go test -v
```

The test suite covers:
- Health endpoint
- Create book (valid and invalid input)
- List books (all and filtered by author)
- Get single book (existing and non-existent)
- Update book
- Delete book (existing and non-existent)
- Invalid book ID handling
