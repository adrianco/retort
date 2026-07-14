# Book API - REST API for Managing a Book Collection

A simple REST API service for managing a book collection, built with Go, Gin framework, and SQLite.

## Features

- **CRUD Operations**: Create, Read, Update, and Delete books
- **Filtering**: Filter books by author
- **Input Validation**: Title and author are required fields
- **Health Check**: Endpoint to verify service status
- **SQLite Storage**: Embedded database for persistent storage

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books` | Create a new book |
| GET | `/books` | List all books (supports `?author=` filter) |
| GET | `/books/{id}` | Get a single book by ID |
| PUT | `/books/{id}` | Update a book |
| DELETE | `/books/{id}` | Delete a book |
| GET | `/health` | Health check endpoint |

## Book Fields

- `title` (string, required): The title of the book
- `author` (string, required): The author of the book
- `year` (integer): The publication year
- `isbn` (string): The ISBN number

## Setup and Run

### Prerequisites

- Go 1.21 or later
- SQLite (usually included with the Go SQLite driver)

### Installation

1. Clone or download the project
2. Navigate to the project directory
3. Install dependencies:

```bash
go mod tidy
```

### Running the Application

```bash
go run app.go
```

The server will start on port `8080` by default.

### Configuration

Environment variables:

- `PORT`: Server port (default: `8080`)
- `DB_PATH`: SQLite database path (default: `books.db`)

Example:

```bash
PORT=3000 DB_PATH=/path/to/db go run app.go
```

## Testing

Run the test suite:

```bash
go test -v
```

## Example Usage

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

### Filter books by author

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

## Response Format

### Success Response

```json
{
  "id": 1,
  "title": "The Great Gatsby",
  "author": "F. Scott Fitzgerald",
  "year": 1925,
  "isbn": "978-0743273565"
}
```

### Error Response

```json
{
  "error": "title is required"
}
```

## HTTP Status Codes

- `200 OK` - Successful GET, PUT
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid input or missing required fields
- `404 Not Found` - Book not found
- `405 Method Not Allowed` - Unsupported HTTP method
- `500 Internal Server Error` - Server error
