# Book API - REST Service

A REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Endpoints

| Method | Endpoint          | Description                  |
|--------|-------------------|------------------------------|
| POST   | /books            | Create a new book            |
| GET    | /books            | List all books               |
| GET    | /books/{id}       | Get a single book by ID      |
| PUT    | /books/{id}       | Update a book                |
| DELETE | /books/{id}       | Delete a book                |
| GET    | /health           | Health check                 |

### Creating a Book (POST /books)

Request body:
```json
{
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

Both `title` and `author` are required fields.

### Listing Books (GET /books)

Returns all books. Supports optional `?author=` query parameter for filtering:
```
GET /books
GET /books?author=F. Scott Fitzgerald
```

## Setup and Run

1. Ensure Go 1.21+ is installed.

2. Install dependencies:
   ```bash
   go mod tidy
   ```

3. Run the server:
   ```bash
   go run app.go
   ```

   The API will be available at `http://localhost:8080`.

4. Optionally set a custom port via the `PORT` environment variable:
   ```bash
   PORT=3000 go run app.go
   ```

## Testing

Run all tests:
```bash
go test -v ./...
```

## Tech Stack

- **Language**: Go 1.21+
- **Framework**: Gin (web framework)
- **Database**: SQLite (via mattn/go-sqlite3)
- **Testing**: Go standard testing package with httptest
