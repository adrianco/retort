# Book API

A REST API service for managing a book collection, built with Go and SQLite.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |

### Create a Book

```bash
curl -X POST http://localhost:8080/books \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}'
```

### List Books

```bash
curl http://localhost:8080/books
curl "http://localhost:8080/books?author=F. Scott Fitzgerald"
```

### Get a Book

```bash
curl http://localhost:8080/books/1
```

### Update a Book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"year":1926}'
```

### Delete a Book

```bash
curl -X DELETE http://localhost:8080/books/1
```

## Setup and Run

```bash
# Install dependencies
go mod tidy

# Run the server
go run .

# Or build and run
go build -o book-api .
./book-api
```

The server starts on port 8080 (configurable via `PORT` env var).

## Tests

```bash
go test ./... -v
```
