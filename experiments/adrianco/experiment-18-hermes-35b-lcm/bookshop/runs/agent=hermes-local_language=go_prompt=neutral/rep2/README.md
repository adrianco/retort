# Book API - REST Service

A REST API service for managing a book collection, built in Go with SQLite.

## Endpoints

| Method | Endpoint       | Description                      |
|--------|----------------|----------------------------------|
| POST   | /books         | Create a new book                |
| GET    | /books         | List all books (optional `?author=` filter) |
| GET    | /books/{id}    | Get a single book by ID          |
| PUT    | /books/{id}    | Update a book                    |
| DELETE | /books/{id}    | Delete a book                    |
| GET    | /health        | Health check                     |

## Setup

### Prerequisites

- Go 1.21 or later

### Running

```bash
# Clone or copy the project
cd bookapi

# Download dependencies
go mod download

# Run the server
go run .
```

The server starts on `http://localhost:8080` by default.

### Configuration

| Environment Variable | Description                  | Default      |
|----------------------|------------------------------|--------------|
| `BOOKAPI_DB`         | Path to the SQLite database  | `./books.db` |
| `PORT`               | Port to listen on            | `8080`       |

## Usage Examples

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
curl "http://localhost:8080/books?author=Fitzgerald"
```

### Get a single book

```bash
curl http://localhost:8080/books/1
```

### Update a book

```bash
curl -X PUT http://localhost:8080/books/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"The Great Gatsby (Updated)"}'
```

### Delete a book

```bash
curl -X DELETE http://localhost:8080/books/1
```

### Health check

```bash
curl http://localhost:8080/health
```

## Validation

- `title` is required
- `author` is required

Validation errors return HTTP 400 with a JSON body:

```json
{
  "error": "validation failed",
  "validation": [
    {"field": "title", "message": "title is required"},
    {"field": "author", "message": "author is required"}
  ]
}
```

## Testing

```bash
go test -v ./...
```

17 tests covering CRUD operations, validation, filtering, error handling, and a full lifecycle test.
