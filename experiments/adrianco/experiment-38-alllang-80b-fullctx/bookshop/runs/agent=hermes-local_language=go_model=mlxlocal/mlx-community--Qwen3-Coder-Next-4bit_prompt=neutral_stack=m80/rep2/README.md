# Book API REST Service

A REST API service for managing a book collection built with Go, Gin, and SQLite.

## Features

- Complete CRUD operations for books
- SQLite database for persistent storage
- Input validation (title and author are required)
- Author filtering when listing books
- Health check endpoint

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /books | List all books (supports `?author=` filter) |
| GET | /books/:id | Get a single book by ID |
| POST | /books | Create a new book |
| PUT | /books/:id | Update a book |
| DELETE | /books/:id | Delete a book |

## Installation

1. Clone this repository
2. Ensure you have Go 1.21 or higher installed
3. Download dependencies:

```bash
go mod tidy
```

## Running the Application

### Development Mode

```bash
go run app.go
```

The server will start on `http://localhost:8080`

### Production Build

```bash
go build -o book-api
./book-api
```

## API Usage Examples

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### List All Books

```bash
curl http://localhost:8080/books
```

### Filter Books by Author

```bash
curl "http://localhost:8080/books?author=F.+Scott+Fitzgerald"
```

### Get a Book by ID

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Great Gatsby (Updated)",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "978-0743273565"
  }'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Testing

Run the test suite:

```bash
go test -v
```

Run tests with coverage:

```bash
go test -v -coverprofile=coverage.out
go tool cover -html=coverage.out
```

## Project Structure

```
.
├── app.go          # Main application with API endpoints
├── app_test.go     # Unit tests
├── go.mod          # Go module dependencies
├── go.sum          # Go module checksums
└── README.md       # This file
```

## License

MIT License
